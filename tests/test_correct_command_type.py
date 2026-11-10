import pytest
from hub.store import Store
from hub.development.selfdevelop import SelfDevelop
from hub.development.commands import dispatch, correct

@pytest.mark.parametrize('command', [None, 123, True])
def test_correct_rejects_non_string_command_without_task_mutation(tmp_path, command):
    store = Store(tmp_path / 'command_type.db')
    chat = SelfDevelop(store).start('Repair command type validation', 'test:command-type', 'mcp')['chat_id']
    task = dispatch(store, chat, 'type-original', 'Inspect', 'Write-Output OK')
    task = store.update(task['id'], state='waiting_user')
    before = store.get(task['id'])
    with pytest.raises(ValueError):
        correct(store, chat, task['id'], before['revision'], 'type-correction', 'Validate command type', command)
    after = store.get(task['id'])
    assert after['revision'] == before['revision']
    assert after['state'] == before['state']
    assert after['result'] == before['result']
