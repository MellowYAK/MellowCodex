import ast
import time
from pathlib import Path
from hub.browser_workflow import completion_check

def test_resumed_task_still_requires_prior_write_verification():
    write={'id':'prior-write','tool':'browser_act','args':{'action':'click'},'result':{'input_sent':True}}
    fresh={'id':'new-read','tool':'browser_observe','result':{'id':'page','elements':[],'text':'Setup completed successfully'}}
    assert completion_check([fresh]) is None
    assert completion_check([write,fresh]) is False
    verified={'id':'assessment','tool':'browser_assess','result':{'status':'success','verified':True,'checked_at':time.time()}}
    assert completion_check([write,fresh,verified]) is True
    assert completion_check([write,fresh,verified,dict(write,id='later-write')]) is False

def test_engine_completion_uses_durable_actions_not_attempt_subset():
    tree=ast.parse((Path(__file__).parents[1]/'hub/engine.py').read_text(encoding='utf-8'))
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='completion_check']
    assert len(calls)==1
    assert isinstance(calls[0].args[0],ast.Name) and calls[0].args[0].id=='actions'
