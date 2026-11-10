"""Read-only Skill Shops API. Code hashes checked, never grants permissions."""
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
        "skills": items, "install_enabled": False, "uninstall_enabled": False,
        "permission_note": "התקנה והסרה דורשות מסלול אישור בעלים ייעודי; אינן פעילות בקטלוג הקריאה.",
    }

def router():
    api = APIRouter()
    @api.get("/api/skill-shops")
    def list_skills():
        return catalog_data()
    @api.get("/api/skill-shops/{name}")
    def detail(name: str):
        if not NAME.fullmatch(name): raise HTTPException(404)
        item = next((x for x in catalog_data()["skills"] if x["name"] == name), None)
        if item is None: raise HTTPException(404)
        return item
    return api
