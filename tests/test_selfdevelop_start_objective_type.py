"""Regression for the actual SelfDevelop.start objective input contract."""
import pytest
from hub.store import Store
from hub.development.selfdevelop import SelfDevelop

@pytest.mark.parametrize('objective', [None, 123, True])
def test_start_rejects_nonstring_objective_without_creating_session(tmp_path, objective):
    store=Store(tmp_path/'s.db')
    service=SelfDevelop(store)
    with pytest.raises(ValueError, match='objective|human'):
        service.start(objective,'test:invalid-objective','mcp')
    with store.connect() as db:
        count=db.execute('SELECT count(*) FROM selfdevelop_sessions').fetchone()[0]
    assert count == 0

def test_start_valid_objective_and_idempotent_same_chat(tmp_path):
    store=Store(tmp_path/'s.db')
    service=SelfDevelop(store)
    first=service.start('Repair local agent safely','test:valid-objective','mcp')
    second=service.start('Repair local agent safely','test:valid-objective','mcp')
    assert second['chat_id']==first['chat_id']
    assert second['objective']=='Repair local agent safely'

@pytest.mark.parametrize('objective', ['', '  ', '\t'])
def test_start_still_rejects_blank_objective(tmp_path, objective):
    store=Store(tmp_path/'s.db')
    service=SelfDevelop(store)
    with pytest.raises(ValueError, match='objective|human'):
        service.start(objective,'test:blank-objective','mcp')
