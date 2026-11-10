"""Skill Shops catalog and owner-authorized local package lifecycle."""
import hashlib
import json
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from .config import ROOT

REPORT = Path("E:/AI/candidates/skills-100-20261109/INTEGRATION-AUDIT-VERIFICATION-LIVE.json")
NAME = re.compile(r"^[a-z][a-z0-9_]{2,60}$")
CAP = re.compile(r"^research100\.\d{3}$")

def safe_text(value, limit=200):
    return str(value or "")[:limit]

def catalog_data(extension_root=None, audit_path=None):
    folder = Path(extension_root) if extension_root is not None else ROOT / "extensions"
    audit = Path(audit_path) if audit_path is not None else REPORT
    evidence = {}
    if audit.is_file():
        try:
            data = json.loads(audit.read_text(encoding="utf8"))
            evidence = {r["source_id"]: r for r in data.get("items", [])
                        if isinstance(r, dict) and CAP.fullmatch(str(r.get("source_id", "")))}
        except (OSError, ValueError, TypeError):
            evidence = {}
    items, unique = [], set()
    for manifest_path in sorted(folder.glob("*/manifest.json")):
        if manifest_path.is_symlink() or manifest_path.parent.is_symlink():
            continue
        try:
            m = json.loads(manifest_path.read_text(encoding="utf8"))
            name, version = m.get("name"), m.get("version")
            if not isinstance(name, str) or not NAME.fullmatch(name):
                continue
            if not isinstance(version, str) or not re.fullmatch("[0-9a-f]{32}", version):
                continue
            source = manifest_path.parent / version / "tool.py"
            verified = (source.is_file() and not source.is_symlink() and
                        hashlib.sha256(source.read_bytes()).hexdigest() == m.get("source_sha256"))
            caps = list(dict.fromkeys(c for c in m.get("capability_ids", [])
                    if isinstance(c, str) and CAP.fullmatch(c)))[:100]
            unique.update(caps)
            categories = m.get("categories", [])
            categories = categories if isinstance(categories, list) else []
            limits = m.get("limitations", [])
            limits = limits if isinstance(limits, list) else []
            items.append({
                "name": name,
                "title": safe_text(m.get("display_name") or name.replace("_", " ").title(), 100),
                "description": safe_text(m.get("description"), 250),
                "version": version,
                "integrity_verified": bool(verified),
                "categories": [safe_text(x, 32) for x in categories[:8] if isinstance(x, str)],
                "limitations": [safe_text(x, 180) for x in limits[:8]],
                "capabilities": [{"id": c, "number": int(c[-3:]),
                      "verification": safe_text(evidence.get(c, {}).get("live_verification") or "unverified", 100),
                      "full_acceptance": evidence.get(c, {}).get("full_real_world_acceptance") is True}
                      for c in caps],
            })
        except (OSError, TypeError, ValueError, KeyError):
            continue
    return {
        "installed_skills": len(items), "mapped_capabilities": len(unique), "original_goal": 100,
        "fully_verified": sum(evidence.get(c, {}).get("full_real_world_acceptance") is True for c in unique),
        "skills": items, "install_enabled": True, "uninstall_enabled": True,
        "permission_note": "התקנה, עדכון והסרה כפופים להרשאות הבעלים של השיחה. החבילות פועלות בהרשאות המשתמש הנוכחי.",
    }


from pydantic import BaseModel
from .skill_shops_lifecycle import SkillShopsLifecycle


class ShopActionRequest(BaseModel):
    action: str
    slug: str
    chat_id: str


class ShopCommitRequest(ShopActionRequest):
    expected_digest: str


def _extension_tasks_busy(_name):
    """Read-only SQLite task gate. Unknown status means no destructive removal."""
    from .config import STATE
    import sqlite3
    from contextlib import closing
    db = STATE / "hub.sqlite3"
    if not db.is_file():
        return True
    try:
        address = f"file:{db.as_posix()}?mode=ro"
        with closing(sqlite3.connect(address, uri=True, timeout=1.0)) as connection:
            states = connection.execute("SELECT state FROM tasks").fetchall()
            if any(state not in ("done", "failed", "cancelled", "waiting_review", "waiting_user", "paused")
                   for (state,) in states):
                return True
            pending = connection.execute("SELECT args FROM actions WHERE state='pending'").fetchall()
        # Historical review cards do not execute code. An unresolved action
        # referencing this package still prevents moving its files.
        return any(_name in args or _name.replace("_", "-") in args for (args,) in pending)
    except (sqlite3.Error, OSError):
        return True


_marketplace = SkillShopsLifecycle(in_use=_extension_tasks_busy)


def router():
    """Legacy read-only catalog. Never mutate or approve through this router."""
    api = APIRouter()

    @api.get("/api/skill-shops")
    def list_skills():
        return catalog_data()

    @api.get("/api/skill-shops/{name}")
    def detail(name: str):
        if not NAME.fullmatch(name):
            raise HTTPException(404, "Unknown skill")
        item = next(
            (x for x in catalog_data()["skills"] if x["name"] == name), None
        )
        if item is None:
            raise HTTPException(404, "Unknown skill")
        return item

    return api


def _require_chat(chat_id):
    from .config import STATE
    import sqlite3
    from contextlib import closing
    with closing(sqlite3.connect(f"file:{(STATE / 'hub.sqlite3').as_posix()}?mode=ro", uri=True)) as db:
        if not db.execute("SELECT 1 FROM chats WHERE id=?", (chat_id,)).fetchone():
            raise HTTPException(404, "Chat not found")


def action_router():
    """Separately mounted, owner-broker-gated lifecycle endpoints."""
    api = APIRouter()

    @api.get("/api/skill-shops/available")
    def local_sources():
        return {"packages": _marketplace.available_packages(),
                "remote_zip_install_supported": False,
                "requires_protected_owner": True}

    @api.post("/api/skill-shops/preview")
    def preview(payload: ShopActionRequest):
        _require_chat(payload.chat_id)
        try:
            return _marketplace.preview(payload.action, payload.slug, payload.chat_id)
        except (ValueError, OSError) as exc:
            raise HTTPException(409, str(exc)[:200]) from exc

    @api.post("/api/skill-shops/commit")
    async def commit(payload: ShopCommitRequest):
        _require_chat(payload.chat_id)
        try:
            return await _marketplace.commit(
                payload.action, payload.slug, payload.expected_digest, payload.chat_id
            )
        except (ValueError, OSError) as exc:
            raise HTTPException(409, str(exc)[:200]) from exc

    return api
