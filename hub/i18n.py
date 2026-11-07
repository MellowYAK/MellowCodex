"""Catalog-backed text for new development capabilities; protocol IDs remain data."""
import json
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=3)
def catalog(language='en'):
    root=Path(__file__).parent/'locales'
    base=json.loads((root/'ru.json').read_text(encoding='utf-8'))
    if language in ('en','he'):
        base.update(json.loads((root/(language+'.json')).read_text(encoding='utf-8')))
    return base

def t(key,language='en',**values):
    return catalog(language)[key].format(**values)

class CapabilityError(ValueError):
    def __init__(self,key,**values):
        self.code=key
        self.values=values
        super().__init__(t(key,**values))
