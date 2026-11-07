"""Persistent screenshot transport settings; originals remain available locally."""
from pathlib import Path
from io import BytesIO
from pydantic import BaseModel, Field
from PIL import Image
from .config import STATE

class ScreenshotSettings(BaseModel):
    enabled: bool = True
    max_edge: int = Field(default=1600, ge=640, le=3840)
    quality: int = Field(default=75, ge=30, le=95)
    chatgpt_max_edge: int = Field(default=1280, ge=640, le=3840)
    chatgpt_quality: int = Field(default=70, ge=30, le=95)
    ocr_assistance: bool = False

def load():
    try:return ScreenshotSettings.model_validate_json((STATE/'screenshot-settings.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):return ScreenshotSettings()

def save(settings):
    path=STATE/'screenshot-settings.json';temporary=path.with_suffix('.tmp')
    temporary.write_text(settings.model_dump_json(),encoding='utf-8');temporary.replace(path)
    return settings.model_dump()

def prepare(path, destination="local"):
    if destination not in ("local", "chatgpt"):raise ValueError("Unknown image destination")
    path=Path(path);settings=load()
    if not settings.enabled:return path
    with Image.open(path) as source:
        picture=source.convert('RGB')
        edge=settings.chatgpt_max_edge if destination=="chatgpt" else settings.max_edge
        quality=settings.chatgpt_quality if destination=="chatgpt" else settings.quality
        picture.thumbnail((edge,edge),Image.Resampling.LANCZOS)
        data=BytesIO();picture.save(data,format='JPEG',quality=quality,optimize=True)
        output=path.with_name(path.stem+'.'+destination+'.transport.jpg')
        output.write_bytes(data.getvalue())
        return output
