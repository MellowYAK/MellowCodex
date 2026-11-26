import asyncio
import json
import pytest
from hub.store import Store
from hub.model_settings import ModelSettings, save_settings, load_settings
from hub import app as hubapp

def test_action_audit(tmp_path):
    store=Store(tmp_path/'audit.db')
    task=store.create('goal',str(tmp_path),'code','request-id')
    aid=store.begin_action(task['id'],'run_shell',{'command':'example'})
    store.end_action(aid,{'exit_code':7})
    store.update(task['id'],state='failed')
    events=store.events(task['id'])
    by={e['kind']:e['data'] for e in events}
    assert by['action_started']['action_id']==aid
    assert by['action_finished']['outcome']=='error'
    assert by['action_finished']['exit_code']==7
    assert by['state']['previous_state']=='queued'
    assert by['state']['action_counts']=={'complete':1}

def test_settings_audit(tmp_path):
    save_settings(ModelSettings(inference_enabled=False),tmp_path)
    rows=[json.loads(s) for s in (tmp_path/'model-settings-audit.jsonl').read_text().splitlines()]
    assert [r['phase'] for r in rows]==['started','committed']
    assert rows[0]['operation_id']==rows[1]['operation_id']
    assert rows[1]['inference_before'] is True and rows[1]['inference_after'] is False
    assert rows[1]['source']['function']=='test_settings_audit'
    assert load_settings(tmp_path).inference_enabled is False

def test_hub_rejects_implicit_mcp_model(tmp_path,monkeypatch):
    from fastapi import HTTPException
    from hub.conversations import Conversations
    store=Store(tmp_path/'requests.db');chats=Conversations(store)
    chat=chats.create(chats.project(tmp_path)['id'])['id']
    monkeypatch.setattr(hubapp,'store',store)
    monkeypatch.setattr(hubapp,'conversations',lambda:chats)
    body=hubapp.ChatMessage(text='create a folder',request_id='direct-block-test',source='mcp')
    with pytest.raises(HTTPException) as err:
        asyncio.run(hubapp.chat_message(chat,body))
    assert err.value.status_code==409
    assert 'DIRECT_ACTION_REQUIRED' in err.value.detail
    row=store.request_audit(chat)[0]
    assert row['phase']=='blocked' and row['data']['actions_executed']==0
    assert row['data']['model_inference'] is False and row['data']['instruction']=='create a folder'
