"""Validated, durable local inference preferences; never stores credentials."""
import json
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal
from .config import MODEL, STATE

class ModelSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    model: str = Field(default=MODEL, min_length=1, max_length=160)
    inference_enabled: bool = True
    coding_model: str = Field(default='', max_length=160)
    context_tokens: int = Field(default=16384, ge=8192, le=131072)
    response_tokens: int = Field(default=1024, ge=256, le=8192)
    temperature: float = Field(default=.1, ge=0, le=1)
    keep_alive_minutes: int = Field(default=30, ge=0, le=1440)
    request_timeout_seconds: int = Field(default=120, ge=30, le=600)
    visual_guidance: bool = True
    visual_policy: Literal['smart','continuous'] = 'smart'

def load_settings(state=STATE):
    try:return ModelSettings.model_validate_json((Path(state)/'model-settings.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):return ModelSettings()

def save_settings(settings,state=STATE):
    path=Path(state)/'model-settings.json';path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(settings.model_dump_json(indent=2),encoding='utf-8');temporary.replace(path)

PRESETS={
    'fast':{'context_tokens':16384,'response_tokens':512,'temperature':.1,'keep_alive_minutes':30},
    'balanced':{'context_tokens':16384,'response_tokens':1024,'temperature':.1,'keep_alive_minutes':30},
    'extended':{'context_tokens':32768,'response_tokens':2048,'temperature':.1,'keep_alive_minutes':30},
}
