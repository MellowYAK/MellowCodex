# Direct MCP default and execution audit

External MCP is the director-to-executor path. Native computer actions and exact shell commands never require local inference. Model-based tasks require explicit use_local_model=true; rejected implicit requests are persisted with zero executed actions.

- direct_command: one exact shell action, existing owner permission gate, atomic request identity and arguments, review before continuation.
- direct_action: one permitted native action, existing schema and stale-observation checks, no inference or policy-control tools.
- Local UI model controls are optional. Model selection is not a fallback for MCP failure.
- Durable task/action events record start, return, state transition and failure classification. A returned action is not semantic verification.
- Model settings changes record start, commit or failure, changed fields and call-site provenance. Historical actor identity cannot be inferred from a false setting.
- Service teardown preserves the persisted inference preference. Verified explicit unload still disables inference.
- Recovery never automatically replays a pending effect.

Validation: 56 focused tests passed in the isolated Windows worktree, including model-forbidden exact shell/native file read, replay fences, explicit model opt-in, request audit, model memory, shutdown, and health diagnostics. Production activation and real visual UI tests are separate acceptance gates.
