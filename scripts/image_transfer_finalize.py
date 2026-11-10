"""Finalize an already-received, verified MellowCodex MCP image by file ID.

Incoming bytes are handled ONLY by existing image_upload_begin/chunk/finish tools.
This registered extension copies a ready library asset to a new local file.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from PIL import Image

MAX_BYTES = 20 * 1024 * 1024
EXTS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG",
        ".webp": "WEBP", ".bmp": "BMP"}


def installed_python():
    """Never invoke bare 'python' from PATH; report the absolute interpreter."""
    path = Path(sys.executable)
    if not path.is_absolute() or not path.is_file():
        raise RuntimeError("No verified absolute installed Python interpreter")
    return str(path.resolve())


def finalize_record(record, destination, expected_sha256, expected_size):
    """Copy a ready MCP image with exclusive creation, hash and decoder checks."""
    if record.get("status") != "ready" or record.get("source") != "mcp-image-transfer":
        raise ValueError("The source is not a ready MCP image transfer")
    if not isinstance(expected_sha256, str) or not re.fullmatch("[a-f0-9]{64}", expected_sha256):
        raise ValueError("Expected SHA-256 must be lowercase 64-character hex")
    if type(expected_size) is not int or not 1 <= expected_size <= MAX_BYTES:
        raise ValueError("Expected image size must be between 1 and 20 MiB")
    if record.get("size") != expected_size or record.get("sha256") != expected_sha256:
        raise ValueError("Registered image metadata differs from the supplied expected size/hash")
    source = Path(record["path"]).resolve(strict=True)
    target = Path(destination)
    if not target.is_absolute() or target.suffix.lower() not in EXTS:
        raise ValueError("Destination must be an absolute supported image filename")
    target = target.resolve(strict=False)
    if target == source:
        raise ValueError("Destination must differ from the source")
    if source.stat().st_size != expected_size:
        raise ValueError("Registered source bytes have changed")
    with source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != expected_sha256:
        raise ValueError("Registered source hash differs from expected hash")
    target.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        # O_EXCL is a true non-overwrite promise even under concurrent invocation.
        with target.open("xb") as out:
            created = True
            with source.open("rb") as inp:
                while True:
                    block = inp.read(512 * 1024)
                    if not block:
                        break
                    out.write(block)
        if target.stat().st_size != expected_size:
            raise ValueError("Destination size verification failed")
        with target.open("rb") as stream:
            saved_hash = hashlib.file_digest(stream, "sha256").hexdigest()
        if saved_hash != expected_sha256:
            raise ValueError("Destination SHA-256 verification failed")
        with Image.open(target) as image:
            fmt = image.format
            dimensions = list(image.size)
            image.load()
        if fmt != EXTS[target.suffix.lower()]:
            raise ValueError("Image decoder format does not match destination extension")
        return {"verified": True, "destination": str(target), "size": expected_size,
                "sha256": saved_hash, "format": fmt, "dimensions": dimensions,
                "python": installed_python()}
    except Exception:
        if created:
            target.unlink(missing_ok=True)
        raise


def main():
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("Expected an object with source_file_id, destination, expected_size, expected_sha256")
        expected_keys = {"source_file_id", "destination", "expected_size", "expected_sha256"}
        if set(payload) != expected_keys:
            raise ValueError("Supply exactly source_file_id, destination, expected_size, expected_sha256")
        file_id = payload["source_file_id"]
        if not isinstance(file_id, str) or not re.fullmatch("[a-f0-9]{32}", file_id):
            raise ValueError("Invalid MellowCodex local file ID")
        # Extensions executes a copied tool.py from its version folder.
        workspace = Path.cwd().resolve()
        if not (workspace / "hub" / "file_library.py").is_file():
            raise RuntimeError("Current Extensions workspace is not the Hub project")
        if str(workspace) not in sys.path:
            sys.path.insert(0, str(workspace))
        from hub.file_library import FileLibrary
        record = FileLibrary().get(file_id, ready=True)
        result = finalize_record(record, payload["destination"],
                                 payload["expected_sha256"], payload["expected_size"])
        result["source_file_id"] = file_id
        print(json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"verified": False, "error": str(exc),
                          "error_type": type(exc).__name__}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
