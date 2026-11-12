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
    context_tokens: int = Field(default=16384, ge=1024)
    response_tokens: int = Field(default=1024, ge=256, le=8192)
    temperature: float = Field(default=.1, ge=0, le=1)
    keep_alive_minutes: int = Field(default=30, ge=0, le=1440)
    request_timeout_seconds: int = Field(default=120, ge=30, le=600)
    context_management: Literal['legacy','shadow','bounded'] = 'shadow'
    working_input_tokens: int = Field(default=12000, ge=2048, le=262144)
    browser_driver: Literal['default','ui_tars'] = 'default'
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


# A single source of persisted model preferences. Chat and MCP use the same
# JSON settings and the same API, never a side-channel or a second store.
import re
from pydantic import ValidationError

FIELD_DESCRIPTIONS = {
    'browser_driver': ('browser task driver: default or ui_tars; UI-TARS requires its local runtime on loopback8794, no Ollama fallback', 'enum', 'next_request'),
    'context_management': ('packet policy: legacy, shadow, bounded; no model allocation change', 'enum', 'next_request'),
    'working_input_tokens': ('soft estimated input target; mandatory evidence may exceed target but never hard budget', 'tokens', 'next_request'),
    'model': ('installed Ollama model ID', 'name', 'next_request'),
    'coding_model': ('installed coding model ID (empty uses primary)', 'name', 'next_request'),
    'inference_enabled': ('allow inference after manual memory control', 'boolean', 'next_request'),
    'context_tokens': ('Ollama num_ctx model context, not conversation compression or tool output', 'tokens', 'next_request_or_reload'),
    'response_tokens': ('Ollama num_predict maximum output tokens', 'tokens', 'next_request'),
    'temperature': ('generation temperature', 'ratio', 'next_request'),
    'keep_alive_minutes': ('Ollama model retention', 'minutes', 'next_request'),
    'request_timeout_seconds': ('HTTP inference timeout', 'seconds', 'next_request'),
    'visual_guidance': ('visual guidance enabled', 'boolean', 'next_request'),
    'visual_policy': ('visual guidance policy', 'enum', 'next_request'),
}

def field_metadata():
    result = {}
    for name, info in ModelSettings.model_fields.items():
        if name not in FIELD_DESCRIPTIONS:
            continue
        description, units, effect = FIELD_DESCRIPTIONS[name]
        metadata = {'type': 'integer' if info.annotation is int else
                    'number' if info.annotation is float else
                    'boolean' if info.annotation is bool else 'string',
                    'units': units, 'default': info.default, 'scope': ['default'],
                    'effect': effect, 'description': description}
        for bound in info.metadata:
            for prop, key in (('ge', 'minimum'), ('gt', 'exclusive_minimum'),
                              ('le', 'maximum'), ('lt', 'exclusive_maximum')):
                if getattr(bound, prop, None) is not None:
                    metadata[key] = getattr(bound, prop)
        if name == 'context_tokens':
            metadata['runtime_limit'] = 'model-specific; verify Ollama /api/show and /api/ps'
            metadata['no_arbitrary_fixed_upper_cap'] = True
        result[name] = metadata
    return result

_FIELD_WORDS = (
    ('context_tokens', ('חלון הקונטקסט', 'חלון הקשר', 'חלון מודל', 'קונטקסט', 'num_ctx', 'context window', 'context length')),
    ('response_tokens', ('מגבלת פלט', 'טוקנים לפלט', 'אורך תשובה', 'num_predict', 'max output', 'response tokens')),
    ('temperature', ('טמפרטורה', 'אקראיות', 'temperature')),
    ('keep_alive_minutes', ('השאר בזיכרון', 'keep alive')),
    ('request_timeout_seconds', ('זמן המתנה לתגובה', 'timeout')),
    ('coding_model', ('מודל תכנות', 'coding model')),
    ('model', ('מודל מקומי', 'מודל ראשי')),
    ('visual_guidance', ('הנחיות חזותיות', 'visual guidance')),
    ('visual_policy', ('מדיניות חזותית', 'visual policy')),
)

def parse_model_command(text):
    """Return a model preference intent, not arbitrary general chat content."""
    if not isinstance(text, str) or not 4 <= len(text) <= 1000:
        return None
    s = text.strip().lower()
    field = next((field for field, words in _FIELD_WORDS if any(w in s for w in words)), None)
    if field is None:
        if (re.search(r'\d+\s*[km]\b', s) and any(word in s for word in ('קבע','הגדל','הגדר','set'))) or s in ('מה הערך הפעיל?', 'מה הערך הפעיל', 'החזר לברירת המחדל'):
            field = 'context_tokens'
        else:
            return None
    scope = 'conversation' if any(w in s for w in ('לשיחה הזאת','לשיחה הזו','בשיחה הזאת','for this chat','this conversation')) else 'default'
    if any(w in s for w in ('מה הערך','מה ההגדרה','מה הקונטקסט','מה חלון','מה מוגדר','מה פעיל','הצג','what is','show','current')):
        return {'action': 'get', 'field': field, 'scope': scope}
    if any(w in s for w in ('ברירת המחדל','אפס את','איפוס','reset','default')) and any(w in s for w in ('החזר','אפס','שחזר','reset','restore','default')):
        return {'action': 'reset', 'field': field, 'scope': scope}
    if not any(w in s for w in ('הגדל','הקטן','קבע','שנה','הגדר','עדכן','שים','set','change','increase','decrease')):
        return None
    if field in ('context_tokens','response_tokens','keep_alive_minutes','request_timeout_seconds','temperature'):
        # Reject ambiguous arithmetic requests rather than silently changing to
        # an amount instead of by an amount.
        if any(w in s for w in ('ב-', 'by ', 'פי ', 'כפול')):
            return {'action': 'error', 'field': field, 'scope': scope, 'error': 'Specify an absolute desired setting'}
        numbers = list(re.finditer(r'(?<![0-9a-z_])(\d+(?:\.\d+)?)\s*([km])?(?![0-9a-z_])', s))
        if len(numbers) != 1:
            return {'action': 'error', 'field': field, 'scope': scope, 'error': 'Specify exactly one numeric value'}
        match = numbers[0]
        value = float(match.group(1)) * (1024 if match.group(2) == 'k' else 1048576 if match.group(2) == 'm' else 1)
        if field != 'temperature':
            if value != int(value):
                return {'action': 'error', 'field': field, 'scope': scope, 'error': 'Token and time settings must be whole numbers'}
            value = int(value)
        return {'action': 'set', 'field': field, 'scope': scope, 'value': value}
    return {'action': 'error', 'field': field, 'scope': scope, 'error': 'Use a supported explicit model preference value through the typed settings tool'}
