"""Owner-only Guard Hub pair startup from immutable installed Guard config.

Executed only by the existing Windows lifecycle reconciler under its mutex.
No user-supplied commands, credentials, port choices or process termination.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path("C:/ProgramData/MellowGuard").resolve()

def load_core():
    installed = json.loads((ROOT / "current.json").read_text(encoding="utf-8"))
    release_id = installed["release_id"]
    if not isinstance(release_id, str) or not __import__("re").fullmatch(r"[A-Za-z0-9.-]+", release_id):
        raise ValueError("Invalid installed Guard release")
    release = (ROOT / "releases" / release_id).resolve(strict=True)
    if release.parent != (ROOT / "releases").resolve(strict=True):
        raise ValueError("Guard release escaped immutable path")
    sys.path.insert(0, str(release))
    from mellow_guard.config import GuardConfig
    from mellow_guard.core import GuardCore
    from mellow_guard.mcp_server import load_local_token
    cfg = GuardConfig(
        home=ROOT,
        hub_root=Path(installed["hub_root"]),
        hub_source=Path(installed["hub_source"]),
        hub_python=Path(installed["hub_python"]),
        staging_root=Path(installed["staging_root"]),
        auth_file=Path(installed["auth_file"]),
        bind=installed.get("bind", "127.0.0.1"),
        port=int(installed["port"]),
        hub_port=int(installed["hub_port"]),
        gateway_port=int(installed["gateway_port"]),
        guard_version=str(installed.get("version", "1.0-contract")),
    )
    credential = load_local_token(cfg.auth_file, cfg.home, cfg.hub_source)
    return GuardCore(cfg), credential

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", action="store_true")
    args = p.parse_args()
    core, credential = load_core()
    if args.start:
        data = core.start_owned_service("hub", credential=credential)
    else:
        data = core.service_status("hub", credential=credential)
    safe = {k:data.get(k) for k in ("healthy","supervisor_healthy","observed_healthy",
                                     "health_basis","owned_pids","started_pids")}
    print(json.dumps(safe))
    return 0 if safe.get("healthy") and (not args.start or safe.get("supervisor_healthy")) else 2

if __name__ == "__main__":
    raise SystemExit(main())