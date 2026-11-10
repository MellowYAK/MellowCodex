"""Verified MCP image transfer and file-id-only Windows wallpaper operation.

The MCP gateway and local Hub share the same FileLibrary directory.
Untrusted client bytes are bounded, hash-verified and checked as actual images.
"""
import base64
import binascii
import ctypes
import hashlib
import json
import os
import re
import shutil
import threading
import uuid
from ctypes import wintypes
from pathlib import Path

from PIL import Image

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_CHUNK_BYTES = 512 * 1024
_ALLOWED = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp", "BMP": "image/bmp"}
_LOCK = threading.RLock()


class ImageTransfer:
    def __init__(self, library):
        self.library = library

    def _pending(self, file_id):
        record = self.library.get(file_id)
        if record["source"] != "mcp-image-transfer" or record["status"] != "receiving":
            raise ValueError("Image transfer is not awaiting data")
        path = Path(record["path"])
        meta = path.with_name(path.name + ".transfer.json")
        if not meta.is_file():
            raise ValueError("Transfer metadata missing")
        return record, path, meta, json.loads(meta.read_text(encoding="utf-8"))

    def begin(self, name, size, sha256):
        if not isinstance(size, int) or isinstance(size, bool) or not 1 <= size <= MAX_IMAGE_BYTES:
            raise ValueError("Image must be between 1 byte and 20 MiB")
        if not isinstance(sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", sha256):
            raise ValueError("SHA-256 must contain 64 lowercase hexadecimal characters")
        if Path(str(name).replace("\\", "/")).suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            raise ValueError("Unsupported image filename extension")
        record = self.library.reserve(name, "mcp-image-transfer", "application/octet-stream")
        path = Path(record["path"])
        path.write_bytes(b"")
        path.with_name(path.name + ".transfer.json").write_text(
            json.dumps({"size": size, "sha256": sha256}), encoding="utf-8")
        return {"file_id": record["id"], "size": size, "received": 0, "sha256": sha256}

    def chunk(self, file_id, offset, data_base64):
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ValueError("Invalid chunk offset")
        if not isinstance(data_base64, str) or len(data_base64) > (MAX_CHUNK_BYTES * 4 // 3) + 8:
            raise ValueError("Image chunk too large")
        try:
            raw = base64.b64decode(data_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Invalid base64 image chunk") from exc
        if not raw or len(raw) > MAX_CHUNK_BYTES:
            raise ValueError("Image chunk must contain 1 to 524288 bytes")
        with _LOCK:
            _, path, _, info = self._pending(file_id)
            received = path.stat().st_size
            if received != offset or received + len(raw) > info["size"]:
                raise ValueError("Incorrect offset or declared image size exceeded")
            with path.open("ab") as output:
                output.write(raw)
            return {"file_id": file_id, "received": received + len(raw), "size": info["size"]}

    def finish(self, file_id):
        with _LOCK:
            _, path, meta, info = self._pending(file_id)
            if path.stat().st_size != info["size"]:
                raise ValueError("Image transfer incomplete")
            with path.open("rb") as source:
                actual = hashlib.file_digest(source, "sha256").hexdigest()
            if actual != info["sha256"]:
                raise ValueError("Image SHA-256 mismatch")
            with Image.open(path) as picture:
                fmt = picture.format
                picture.verify()
            if fmt not in _ALLOWED:
                raise ValueError("Unsupported image encoding")
            with self.library.connect() as db:
                db.execute("UPDATE files SET mime=? WHERE id=?", (_ALLOWED[fmt], file_id))
            ready = self.library.finish(file_id)
            meta.unlink(missing_ok=True)
            return {key: ready[key] for key in ("id", "name", "mime", "size", "sha256", "status")}


def set_wallpaper(library, file_id, *, pictures_dir=None, user32=None):
    """Copy an already registered image to Pictures, set, and read back Windows state."""
    item = library.get(file_id, ready=True)
    if item["mime"] not in _ALLOWED.values() or item["size"] > MAX_IMAGE_BYTES:
        raise ValueError("Wallpaper must be a verified image under 20 MiB")
    source = Path(item["path"])
    with source.open("rb") as data:
        if hashlib.file_digest(data, "sha256").hexdigest() != item["sha256"]:
            raise ValueError("Registered image bytes changed")
    with Image.open(source) as picture:
        fmt = picture.format
        picture.verify()
    if _ALLOWED.get(fmt) != item["mime"]:
        raise ValueError("Stored image MIME does not match content")
    if user32 is None:
        if os.name != "nt":
            raise RuntimeError("Windows wallpaper API is unavailable on this operating system")
        user32 = ctypes.WinDLL("user32", use_last_error=True)
    target_dir = Path(pictures_dir) if pictures_dir else Path.home() / "Pictures"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / ("MellowCodex-" + uuid.uuid4().hex + "." +
                           {"PNG": "png", "JPEG": "jpg", "WEBP": "webp", "BMP": "bmp"}[fmt])
    shutil.copy2(source, target)
    absolute = str(target.resolve())
    if not user32.SystemParametersInfoW(20, 0, absolute, 3):
        raise RuntimeError("Windows rejected the wallpaper change")
    observed = ctypes.create_unicode_buffer(32768)
    if not user32.SystemParametersInfoW(0x0073, len(observed), observed, 0):
        raise RuntimeError("Windows did not allow wallpaper readback")
    active = str(Path(observed.value).resolve())
    if os.path.normcase(active) != os.path.normcase(absolute):
        raise RuntimeError("Wallpaper readback differs from the requested file")
    return {"verified": True, "file_id": file_id, "wallpaper_path": absolute}
