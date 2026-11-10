"""Focused independent functional acceptance for image_transfer_finalize tool."""
import hashlib
from pathlib import Path
import tempfile
import tool
from PIL import Image

with tempfile.TemporaryDirectory() as directory:
    d = Path(directory)
    source = d / "incoming.png"
    Image.new("RGB", (3, 2), (22, 44, 66)).save(source, format="PNG")
    raw = source.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    rec = {"source": "mcp-image-transfer", "status": "ready",
           "size": len(raw), "sha256": sha, "path": str(source)}
    dest = d / "final" / "saved.png"
    result = tool.finalize_record(rec, str(dest), sha, len(raw))
    assert result["verified"] and dest.read_bytes() == raw
    assert result["format"] == "PNG" and result["dimensions"] == [3, 2]
    assert Path(result["python"]).is_file()
    try:
        tool.finalize_record(rec, str(dest), sha, len(raw))
        raise AssertionError("Existing destination unexpectedly overwritten")
    except FileExistsError:
        pass
    assert dest.read_bytes() == raw
    mismatch = d / "not_created.png"
    try:
        tool.finalize_record(rec, str(mismatch), "0"*64, len(raw))
        raise AssertionError("Mismatched source SHA unexpectedly accepted")
    except ValueError:
        pass
    assert not mismatch.exists()
print("FOCUSED_FINALIZE_PASS verified real PNG decode, hash, exclusive output and mismatch rejection")
