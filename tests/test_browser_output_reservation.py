import ast
from pathlib import Path

def test_preflight_and_dispatch_use_same_response_reservation():
    tree=ast.parse(Path('hub/ui_tars.py').read_text(encoding='utf-8'))
    fn=next(n for n in ast.walk(tree) if isinstance(n,ast.AsyncFunctionDef) and n.name=='_chat')
    values={}
    for n in ast.walk(fn):
        if isinstance(n,ast.Dict):
            for k,v in zip(n.keys,n.values):
                if isinstance(k,ast.Constant) and k.value in ('max_tokens','response_tokens'):
                    values.setdefault(k.value,[]).append(ast.unparse(v))
    assert values['max_tokens']==['response_tokens']
    assert all(v=='response_tokens' for v in values['response_tokens'])
    guards=[ast.unparse(n.test) for n in ast.walk(fn) if isinstance(n,ast.If)]
    assert 'estimate + response_tokens > 4096' in guards
