"""P13: policy-constrained, deterministic reasoning/model selection.

Routing is metadata-only: it never calls a model, sends private context to the
cloud, changes ModelSettings, or bypasses Guard/OwnerBroker. Providers must be
explicitly registered and measured. This module is a shadow router until P14.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Iterable
import math
import uuid

from .contracts import DecisionRecord


class RouteError(RuntimeError):
    pass


class ComputeMode(str, Enum):
    NONE = "no_model"
    FAST_LOCAL = "fast_local"
    DEEP_LOCAL = "deep_local"
    CLOUD = "cloud"


class ProviderHealth(str, Enum):
    HEALTHY = "healthy"
    UNKNOWN = "unknown"
    CIRCUIT_OPEN = "circuit_open"


@dataclass(frozen=True)
class ProviderProfile:
    id: str
    provider: str
    model: str
    location: str  # local or cloud
    capabilities: FrozenSet[str]
    max_context: int
    supports_reasoning: bool
    supports_tools: bool
    median_latency_ms: int
    measured_quality: float
    tool_success_rate: float
    estimated_usd_per_1k_tokens: float = 0.0
    health: ProviderHealth = ProviderHealth.UNKNOWN
    enabled: bool = True

    def __post_init__(self):
        if not self.id or not self.provider or not self.model:
            raise ValueError("Provider must have stable identity")
        if self.location not in ("local", "cloud"):
            raise ValueError("Provider location must be local or cloud")
        if self.max_context < 1 or self.median_latency_ms < 0:
            raise ValueError("Invalid context/latency")
        if not (0 <= self.measured_quality <= 1 and 0 <= self.tool_success_rate <= 1):
            raise ValueError("Quality scores must be normalized")
        if not math.isfinite(self.estimated_usd_per_1k_tokens) or self.estimated_usd_per_1k_tokens < 0:
            raise ValueError("Cost must be finite and nonnegative")
        if not self.capabilities:
            raise ValueError("Capability declaration cannot be empty")


@dataclass(frozen=True)
class RoutingRequest:
    task_id: str
    plan_version: int
    required_capabilities: FrozenSet[str]
    complexity: float
    uncertainty: float
    context_tokens: int
    deterministic: bool = False
    needs_tools: bool = False
    sensitive: bool = False
    policy_allow_cloud: bool = False
    user_cloud_approved: bool = False
    expected_output_tokens: int = 0
    max_estimated_cost_usd: float | None = None
    prior_failures: int = 0

    def __post_init__(self):
        if not self.task_id or self.plan_version < 1:
            raise ValueError("Routing needs task and version")
        if not (0 <= self.complexity <= 1 and 0 <= self.uncertainty <= 1):
            raise ValueError("Complexity and uncertainty must be normalized")
        if min(self.context_tokens,self.expected_output_tokens,self.prior_failures) < 0:
            raise ValueError("Token count and retries cannot be negative")
        if self.max_estimated_cost_usd is not None:
            if (not math.isfinite(self.max_estimated_cost_usd)
                or self.max_estimated_cost_usd < 0):
                raise ValueError("Invalid cost ceiling")


@dataclass(frozen=True)
class RoutingDecision:
    task_id: str
    plan_version: int
    mode: ComputeMode
    provider_id: str | None
    think: bool
    reason_code: str
    fallback_provider_ids: tuple[str, ...] = ()
    score: float = 0.0

    def decision_record(self) -> DecisionRecord:
        return DecisionRecord(
            decision_id=uuid.uuid4().hex,
            task_id=self.task_id,plan_version=self.plan_version,
            decision=self.mode.value,reason_code=self.reason_code,
            chosen_strategy=self.provider_id or "deterministic_no_model",
            model_reference=self.provider_id,
        )


class ProviderRegistry:
    """Never discovers remote providers implicitly or accepts raw credentials."""
    def __init__(self, profiles: Iterable[ProviderProfile] = ()):
        self._items: dict[str,ProviderProfile] = {}
        for profile in profiles:
            self.register(profile)

    def register(self, profile: ProviderProfile) -> None:
        if profile.id in self._items:
            raise ValueError("Duplicate provider ID")
        self._items[profile.id] = profile

    def replace_health(self, provider_id: str, health: ProviderHealth) -> None:
        from dataclasses import replace
        profile = self._items[provider_id]
        if not isinstance(health,ProviderHealth):
            raise ValueError("Unsupported provider health")
        self._items[provider_id] = replace(profile,health=health)

    def profiles(self) -> tuple[ProviderProfile,...]:
        return tuple(self._items.values())


def _estimated_cost(profile:ProviderProfile,request:RoutingRequest)->float:
    return profile.estimated_usd_per_1k_tokens * (
        request.context_tokens+request.expected_output_tokens)/1000


def _score(profile:ProviderProfile,request:RoutingRequest,deep:bool)->float:
    latency = 1.0/(1.0+profile.median_latency_ms/1500.0)
    context = min(1.0,profile.max_context/max(1,request.context_tokens
                                             +request.expected_output_tokens))
    cost = 1.0/(1.0+_estimated_cost(profile,request)/0.05)
    quality = profile.measured_quality
    if deep:
        base = .43*quality+.21*profile.tool_success_rate+.10*latency+.10*context+.08*cost
        if profile.supports_reasoning:
            base += .10
        if profile.location=="cloud" and request.complexity>=.80:
            base += .13
    else:
        base = .18*quality+.13*profile.tool_success_rate+.42*latency+.13*context+.10*cost
    if profile.location=="local":
        base += .08
    if profile.health == ProviderHealth.UNKNOWN:
        base -= .06
    return round(base,8)


def route(request: RoutingRequest, registry: ProviderRegistry) -> RoutingDecision:
    if request.deterministic:
        return RoutingDecision(request.task_id,request.plan_version,ComputeMode.NONE,None,
                               False,"deterministic_verified_path")
    deep=(request.complexity>=.65 or request.uncertainty>=.60 or request.prior_failures>=2)
    choices=[]
    for profile in registry.profiles():
        if not profile.enabled or profile.health==ProviderHealth.CIRCUIT_OPEN:
            continue
        if not request.required_capabilities.issubset(profile.capabilities):
            continue
        if request.needs_tools and not profile.supports_tools:
            continue
        if profile.max_context < request.context_tokens+request.expected_output_tokens:
            continue
        if deep and not profile.supports_reasoning:
            continue
        if profile.location=="cloud":
            if (request.sensitive or not request.policy_allow_cloud
                or not request.user_cloud_approved):
                continue
        if (request.max_estimated_cost_usd is not None
            and _estimated_cost(profile,request)>request.max_estimated_cost_usd):
            continue
        choices.append((_score(profile,request,deep),profile.id,profile))
    if not choices:
        raise RouteError("No policy-compliant healthy model; do not silently route to cloud")
    choices.sort(key=lambda x:(-x[0],x[1]))
    score,_,profile=choices[0]
    mode=(ComputeMode.CLOUD if profile.location=="cloud" else
          ComputeMode.DEEP_LOCAL if deep else ComputeMode.FAST_LOCAL)
    return RoutingDecision(
        task_id=request.task_id,plan_version=request.plan_version,
        mode=mode,provider_id=profile.id,think=deep and profile.supports_reasoning,
        reason_code=("complex_or_uncertain_request" if deep else "fast_policy_candidate"),
        fallback_provider_ids=tuple(x[1] for x in choices[1:]),
        score=score,
    )
