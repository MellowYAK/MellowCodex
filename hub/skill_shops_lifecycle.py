"""Bounded local skill lifecycle using the installed owner policy service."""
from __future__ import annotations
import asyncio
import ast
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from .config import ROOT
from .owner_broker import owner_status, authorize_action

PACKAGE_ID = re.compile(r"^[a-z][a-z0-9_-]{2,60}$")
ACTIONS = {"install", "update", "remove"}
def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()

def protected_authorize(plan):
    """Consume existing owner policy, never create grants or claim fresh presence."""
    chat = plan["chat_id"]
    state = owner_status(chat)
    if not state.get("installed") or not state.get("server_identity_verified"):
        return {"allowed": False, "reason": "owner_broker_unavailable"}
    request = {"command": "authorize", "chat_id": chat,
               "task_id": "skillshop-" + digest(plan)[:24],
               "action_id": "skillshop-" + digest(plan),
               "operation": "skill_shops_lifecycle", "plan_digest": digest(plan),
               "action": plan["action"], "skill_name": plan["installed_name"],
               "policy_revision": state["policy_revision"]}
    # Request strings are restricted ASCII identifiers; canonical serialization
    # matches the broker's sorted JavaScriptSerializer contract.
    binding = digest(request)
    response = authorize_action(request)
    mode = state.get("effective")
    allowed = (response.get("ok") is True and response.get("allowed") is True
               and response.get("server_identity_verified") is True
               and response.get("policy_revision") == state["policy_revision"]
               and ((mode == "full" and response.get("binding") == binding)
                    or (mode == "ask" and response.get("reason") == "owner_approved"
                        and response.get("request_id") == binding)))
    return {"allowed": allowed, "approved_action_digest": digest(plan) if allowed else None,
            "server_identity_verified": response.get("server_identity_verified") is True,
            "authorization_mode": mode, "request_id": response.get("request_id"),
            "reason": response.get("reason", "existing_owner_policy" if allowed else "binding_or_policy_not_verified"),
            "fresh_owner_presence": False}

class SkillShopsLifecycle:
    def __init__(self, *, source_root=None, extensions_root=None, quarantine=None,
                 authorizer=None, in_use=None):
        self.source_root = Path(source_root or Path(__file__).resolve().parents[1] / "scripts" / "skills").resolve()
        self.extensions_root = Path(extensions_root or ROOT / "extensions").resolve()
        self.quarantine = Path(quarantine or ROOT / "candidates" / "skill-shops-quarantine").resolve()
        self.authorizer = authorizer or protected_authorize
        self.in_use = in_use or (lambda name: True)
        self.lock = asyncio.Lock()

    def _name(self, value):
        if not isinstance(value, str) or not PACKAGE_ID.fullmatch(value):
            raise ValueError("A valid local package slug is required")
        return value.replace("-", "_")

    @staticmethod
    def _contained(path, root):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError("Links and junctions are not permitted")
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("Path escapes allowed root")
        parent = path.parent
        while parent != root and parent.is_relative_to(root):
            if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
                raise ValueError("Linked parent is not permitted")
            parent = parent.parent
        return path

    def _source(self, slug):
        name = self._name(slug)
        folder = self._contained(self.source_root / slug, self.source_root)
        if not folder.is_dir():
            raise ValueError("Only bundled local skill folders may be installed")
        payload = {}
        for filename in ("tool.py", "test_tool.py"):
            path = self._contained(folder / filename, self.source_root)
            if not path.is_file() or path.stat().st_size > 2_000_000:
                raise ValueError("Bounded tool.py and test_tool.py are required")
            data = path.read_bytes()
            ast.parse(data, filename=filename)
            payload[filename] = data
        # This is static syntax validation, not an OS sandbox or malware verdict.
        return name, payload

    def _installed(self, name):
        folder = self._contained(self.extensions_root / name, self.extensions_root)
        path = self._contained(folder / "manifest.json", self.extensions_root)
        if not path.is_file():
            return None
        obj = json.loads(path.read_text(encoding="utf-8"))
        version = obj.get("version")
        if obj.get("name") != name or not isinstance(version, str) or not re.fullmatch(r"[0-9a-f]{32}", version):
            raise ValueError("Invalid installed manifest")
        code = self._contained(folder / version / "tool.py", self.extensions_root)
        if not code.is_file() or hashlib.sha256(code.read_bytes()).hexdigest() != obj.get("source_sha256"):
            raise ValueError("Installed source integrity failed")
        return obj

    def available_packages(self):
        items = []
        if not self.source_root.is_dir():
            return items
        seen = set()
        for folder in sorted(self.source_root.iterdir()):
            if not folder.is_dir():
                continue
            try:
                name, payload = self._source(folder.name)
                if name in seen:
                    raise ValueError("Package slug collision")
                seen.add(name)
                items.append({"slug": folder.name, "name": name,
                              "source_sha256": hashlib.sha256(payload["tool.py"]).hexdigest(),
                              "test_sha256": hashlib.sha256(payload["test_tool.py"]).hexdigest(),
                              "installed": self._installed(name) is not None,
                              "requires_owner": True, "source": str(folder),
                              "permissions": ["Run Python under the current Windows account"],
                              "scan": "syntax_and_path_checks_only"})
            except (OSError, ValueError, SyntaxError, TypeError):
                continue
        return items

    def preview(self, action, slug, chat_id=""):
        if action not in ACTIONS:
            raise ValueError("Unsupported action")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{8,100}", chat_id):
            raise ValueError("Select an existing chat before managing skills")
        name = self._name(slug)
        current = self._installed(name)
        if action == "install" and (current is not None or (self.extensions_root / name).exists()):
            raise ValueError("Target exists; refusing overwrite")
        if action in ("update", "remove") and current is None:
            raise ValueError("Skill is not installed")
        source = None
        if action != "remove":
            _, payload = self._source(slug)
            source = {key: hashlib.sha256(data).hexdigest() for key, data in payload.items()}
        plan = {"operation": "skill_shops_lifecycle", "action": action, "slug": slug,
                "installed_name": name, "chat_id": chat_id, "source": source,
                "current_manifest_digest": digest(current) if current else None,
                "source_root": str(self.source_root), "extensions_root": str(self.extensions_root),
                "risk": "CURRENT_USER_PYTHON_EXECUTION"}
        return {"action": action, "name": name, "slug": slug, "digest": digest(plan),
                "plan": plan, "executed": False, "requires_owner_policy": True,
                "permissions": ["Run skill and its test as current Windows user"],
                "scan": "Syntax and path checks; no claim of malware isolation"}

    async def commit(self, action, slug, expected_digest, chat_id=""):
        if not isinstance(expected_digest, str) or not re.fullmatch(r"[a-f0-9]{64}", expected_digest):
            raise ValueError("Exact preview SHA256 required")
        async with self.lock:
            before = self.preview(action, slug, chat_id)
            if before["digest"] != expected_digest:
                raise ValueError("Stale plan; preview again")
            name = before["name"]
            old = self._installed(name)
            if action in ("remove", "update") and self.in_use(name):
                return {"status": "blocked_in_use", "executed": False}
            if action == "remove" and any(str(x).startswith("research100.") for x in old.get("capability_ids", [])):
                return {"status": "blocked_coverage", "executed": False}
            payload = self._source(slug)[1] if action != "remove" else None
            authorization = self.authorizer(before["plan"])
            if not (isinstance(authorization, dict) and authorization.get("allowed") is True
                    and authorization.get("server_identity_verified") is True
                    and authorization.get("approved_action_digest") == expected_digest):
                return {"status": "needs_owner", "executed": False,
                        "request_id": authorization.get("request_id") if isinstance(authorization, dict) else None,
                        "detail": "Existing owner policy denied or requires approval in Owner Control"}
            if self.preview(action, slug, chat_id)["digest"] != expected_digest:
                return {"status": "stale_after_authorization", "executed": False}
            folder = self.extensions_root / name
            self.quarantine.mkdir(parents=True, exist_ok=True)
            if action == "remove":
                target = self.quarantine / (name + "-" + uuid.uuid4().hex)
                folder.rename(target)
                return {"status": "removed_to_quarantine", "executed": True,
                        "name": name, "quarantine": str(target)}
            # Test an immutable byte snapshot. Never execute mutable source files,
            # and never publish a manifest until this exact snapshot passes.
            self.extensions_root.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix=".shop-", dir=self.extensions_root))
            version = uuid.uuid4().hex
            try:
                for filename, data in payload.items():
                    (staging / filename).write_bytes(data)
                process = await asyncio.create_subprocess_exec(
                    sys.executable, "test_tool.py", cwd=str(staging),
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                    creationflags=getattr(__import__("subprocess"), "CREATE_NO_WINDOW", 0))
                try:
                    result = await asyncio.wait_for(process.wait(), 30)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    process.kill()
                    await process.wait()
                    raise
                if result != 0:
                    return {"status": "validation_failed", "executed": False, "name": name}
                if any((staging / key).read_bytes() != value for key, value in payload.items()):
                    return {"status": "snapshot_changed", "executed": False}
                if self.preview(action, slug, chat_id)["digest"] != expected_digest:
                    return {"status": "source_changed_during_commit", "executed": False}
                manifest = dict(old or {})
                manifest.update(name=name, description=f"Local Skill Shops package: {slug}",
                                version=version, python=sys.executable,
                                source_sha256=hashlib.sha256(payload["tool.py"]).hexdigest(),
                                test_sha256=hashlib.sha256(payload["test_tool.py"]).hexdigest(),
                                requirements=[], validated=True, source_slug=slug,
                                created_by_task="skill-shop-" + expected_digest[:24])
                if old:
                    backup = self.quarantine / (name + "-" + old["version"] + "-manifest.json")
                    if not backup.exists():
                        backup.write_text(json.dumps(old, indent=2), encoding="utf-8")
                    staging.rename(folder / version)
                    temporary = folder / ("manifest." + uuid.uuid4().hex + ".tmp")
                    try:
                        temporary.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                        os.replace(temporary, folder / "manifest.json")
                    finally:
                        temporary.unlink(missing_ok=True)
                else:
                    package = Path(tempfile.mkdtemp(prefix=".package-", dir=self.extensions_root))
                    try:
                        staging.rename(package / version)
                        (package / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
                        package.rename(folder)
                    finally:
                        if package.exists():
                            shutil.rmtree(package)
                return {"status": "installed" if action == "install" else "updated",
                        "executed": True, "name": name, "version": version,
                        "source_sha256": manifest["source_sha256"], "functional_test_passed": True}
            finally:
                if staging.exists():
                    shutil.rmtree(staging)
