"""Restricted director steps never bootstrap forbidden broad project reads."""
import asyncio
from hub.store import Store
from hub.development.selfdevelop import SelfDevelop
from hub.engine import Engine
from hub.context.runtime import prepare


def test_restricted_selfdevelop_step_skips_unallowed_context_bootstrap(tmp_path):
    store=Store(tmp_path/'state.sqlite3')
    service=SelfDevelop(store)
    chat=service.start('Bounded source repair','test:restricted-bootstrap','mcp')
    task=service.step(chat['chat_id'],'scoped-context-001',
                      'Create isolated candidate only',['candidate_create'],
                      required_tools=['candidate_create'])
    engine=Engine(store)
    messages=[{'role':'system','content':'Fixed instructions'},
              {'role':'user','content':'Original objective'}]
    asyncio.run(prepare(engine,task,messages))
    assert store.actions(task['id'])==[]
    assert any(e['kind']=='source_navigation_delegated' for e in store.events(task['id']))
    assert messages[0]['content']=='Fixed instructions'
