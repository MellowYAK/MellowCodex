import pytest
from hub.store import Store
from hub.development.selfdevelop import SelfDevelop
from hub.development.commands import dispatch,correct

@pytest.mark.parametrize('timeout',[True,False,1.5,'60',None,0,181])
def test_correct_rejects_invalid_timeout_without_task_mutation(tmp_path,timeout):
    store=Store(tmp_path/'state.db')
    chat=SelfDevelop(store).start('Repair own timeout validation','test:timeout','mcp')['chat_id']
    task=dispatch(store,chat,'timeout-original','Inspect','Write-Output OK')
    task=store.update(task['id'],state='waiting_user')
    before=store.get(task['id'])['revision']
    with pytest.raises(ValueError):
        correct(store,chat,task['id'],before,'timeout-correction','Correct failure','Write-Output FIXED',timeout=timeout)
    assert store.get(task['id'])['revision']==before
    assert store.get(task['id'])['state']=='waiting_user'

@pytest.mark.parametrize('shell,command',[('bash','echo OK'),('powershell',' '),('cmd','x'*20001)])
def test_correct_preserves_command_guards(tmp_path,shell,command):
    store=Store(tmp_path/'guards.db')
    chat=SelfDevelop(store).start('Repair command validation','test:guards','mcp')['chat_id']
    task=dispatch(store,chat,'guard-original','Inspect','Write-Output OK')
    task=store.update(task['id'],state='waiting_user')
    before=task['revision']
    with pytest.raises(ValueError):
        correct(store,chat,task['id'],before,'guard-correction','Preserve validation',command,shell=shell,timeout=60)
    assert store.get(task['id'])['revision']==before
    assert store.get(task['id'])['state']=='waiting_user'
