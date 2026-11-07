import json
from pathlib import Path

MODES=('background','split')

def load_presentation(state):
    try:
        mode=json.loads((Path(state)/'ui-preferences.json').read_text(encoding='utf-8'))['chatgpt_presentation']
        return mode if mode in MODES else 'split'
    except (OSError,ValueError,KeyError,TypeError):return 'split'

def save_presentation(state,mode):
    if mode not in MODES:raise ValueError('Choose background or split')
    save_preference(state,'chatgpt_presentation',mode)

def save_preference(state,key,value):
    path=Path(state)/'ui-preferences.json';path.parent.mkdir(parents=True,exist_ok=True)
    try:data=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):data={}
    data[key]=value
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(data),encoding='utf-8');temporary.replace(path)

def load_input_mode(state):
    try:mode=json.loads((Path(state)/'ui-preferences.json').read_text(encoding='utf-8'))['input_mode']
    except (OSError,ValueError,KeyError,TypeError):return 'auto'
    return mode if mode in ('auto','quiet','physical') else 'auto'

def save_input_mode(state,mode):
    if mode not in ('auto','quiet','physical'):raise ValueError('Choose auto, quiet or physical')
    save_preference(state,'input_mode',mode)
