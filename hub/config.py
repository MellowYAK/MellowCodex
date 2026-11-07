import os
from pathlib import Path

ROOT = Path(os.environ.get("LOCAL_AGENT_ROOT", "E:/AI"))
STATE = ROOT / "state"
ARTIFACTS = ROOT / "artifacts"
OLLAMA = os.environ.get("LOCAL_AGENT_OLLAMA", "http://127.0.0.1:11434")
MODEL = os.environ.get("LOCAL_AGENT_MODEL", "qwen3.5:4b")
PORT = int(os.environ.get("LOCAL_AGENT_PORT", "8876"))
CDP_PORT = int(os.environ.get('LOCAL_AGENT_CDP_PORT','9223'))
if not 1024<=CDP_PORT<=65535:raise ValueError('Invalid loopback browser port')
import hashlib
DESKTOP_IPC = 'LocalAgentHubDesktop' + ('' if ROOT.resolve()==Path('E:/AI').resolve() else '-'+hashlib.sha256(str(ROOT.resolve()).casefold().encode()).hexdigest()[:16])
for folder in (STATE, ARTIFACTS, ROOT / "repos"):
    folder.mkdir(parents=True, exist_ok=True)

UI_ORIGINS = tuple(f"http://{host}:{PORT}" for host in ("127.0.0.1", "localhost", "100.78.233.10"))
