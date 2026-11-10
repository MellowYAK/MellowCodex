"""Shared, local-only skill icon preferences for the UI and MCP."""
import base64
import binascii
import io
import re
import sqlite3
import xml.etree.ElementTree as ET
from contextlib import closing
from pathlib import Path
from PIL import Image
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from .config import STATE, ROOT

MAX_BYTES = 512 * 1024
NAME = re.compile(r"^[a-z][a-z0-9_]{2,60}$")
SVG_TAGS = set("svg g defs path rect circle ellipse line polyline polygon title desc linearGradient radialGradient stop clipPath mask use symbol".split())
SVG_ATTRS = set("id viewBox width height x y x1 x2 y1 y2 cx cy r rx ry d points fill stroke stroke-width stroke-linecap stroke-linejoin stroke-miterlimit stroke-dasharray stroke-dashoffset fill-rule clip-rule opacity fill-opacity stroke-opacity transform gradientTransform gradientUnits spreadMethod offset stop-color stop-opacity clip-path mask preserveAspectRatio href".split())

def normalize_icon(data_uri):
    if not isinstance(data_uri, str) or len(data_uri) > MAX_BYTES * 4 // 3 + 100:
        raise ValueError("Icon must be at most 512 KB")
    match = re.fullmatch(r"data:image/(png|jpeg|webp|gif|x-icon|vnd.microsoft.icon|svg\+xml);base64,([A-Za-z0-9+/=\r\n]+)", data_uri)
    if not match:
        raise ValueError("Choose PNG, JPEG, WebP, GIF, ICO or static SVG")
    try:
        raw = base64.b64decode(match[2], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid image encoding") from exc
    if len(raw) > MAX_BYTES:
        raise ValueError("Icon must be at most 512 KB")
    if match[1] == "svg+xml":
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
            raise ValueError("SVG entities are not supported")
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise ValueError("Invalid SVG") from exc
        if root.tag not in ("svg", "{http://www.w3.org/2000/svg}svg"):
            raise ValueError("Expected an SVG image")
        nodes = list(root.iter())
        if len(nodes) > 2000:
            raise ValueError("SVG is too complex")
        for node in nodes:
            tag = node.tag.removeprefix("{http://www.w3.org/2000/svg}")
            if tag not in SVG_TAGS:
                raise ValueError("SVG must contain only static vector shapes")
            for attr, value in node.attrib.items():
                key = attr.removeprefix("{http://www.w3.org/1999/xlink}")
                if key not in SVG_ATTRS:
                    raise ValueError("Unsupported SVG attribute: " + key)
                if key == "href" and not re.fullmatch(r"#[A-Za-z_][\w.-]*", value):
                    raise ValueError("External SVG references are not allowed")
                if "url" in value.lower() and not re.fullmatch(r"url\(#[A-Za-z_][\w.-]*\)", value):
                    raise ValueError("Only internal SVG paint references are allowed")
        raw = ET.tostring(root, encoding="utf-8")
        mime = "image/svg+xml"
    else:
        try:
            with Image.open(io.BytesIO(raw)) as image:
                if image.width * image.height > 16_000_000:
                    raise ValueError("Image dimensions are too large")
                image = image.convert("RGBA")
                image.thumbnail((256, 256), Image.Resampling.LANCZOS)
                output = io.BytesIO()
                image.save(output, format="PNG")
                raw = output.getvalue()
        except (OSError, Image.DecompressionBombError) as exc:
            raise ValueError("Invalid image") from exc
        mime = "image/png"
    return "data:" + mime + ";base64," + base64.b64encode(raw).decode("ascii")

def _database(state):
    path = Path(state) / "skill-icons.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    db.execute("CREATE TABLE IF NOT EXISTS icons (name TEXT PRIMARY KEY, data_uri TEXT NOT NULL)")
    return db

def load_icons(state=None):
    state = STATE if state is None else state
    if not (Path(state) / "skill-icons.sqlite3").exists():
        return {}
    with closing(_database(state)) as db:
        return dict(db.execute("SELECT name, data_uri FROM icons"))

def icon_settings(name, data_uri=None, reset=False, state=None, extension_root=None):
    if not NAME.fullmatch(name):
        raise ValueError("Invalid skill name")
    folder = Path(ROOT / "extensions" if extension_root is None else extension_root) / name
    if not (folder / "manifest.json").is_file():
        raise ValueError("Skill is not installed")
    if reset and data_uri is not None:
        raise ValueError("Choose an image or reset, not both")
    state = STATE if state is None else state
    if reset or data_uri is not None:
        value = normalize_icon(data_uri) if data_uri is not None else None
        with closing(_database(state)) as db, db:
            if reset:
                db.execute("DELETE FROM icons WHERE name=?", (name,))
            else:
                db.execute("INSERT OR REPLACE INTO icons VALUES (?, ?)", (name, value))
    value = load_icons(state).get(name)
    return {"name": name, "icon_image": value, "custom": value is not None,
            "active": True, "restart_required": False}

class IconRequest(BaseModel):
    name: str
    data_uri: str | None = Field(default=None, max_length=MAX_BYTES * 4 // 3 + 100)
    reset: bool = False

def router():
    api = APIRouter()
    @api.get("/api/settings/skill-icons/{name}")
    def read(name: str):
        try:
            return icon_settings(name)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    @api.post("/api/settings/skill-icons")
    def write(payload: IconRequest):
        try:
            return icon_settings(**payload.model_dump())
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    return api
