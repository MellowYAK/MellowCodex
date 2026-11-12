import tempfile, unittest, json
from pathlib import Path
from hub.store import Store, now
from hub.conversations import Conversations
from hub.file_library import FileLibrary
from hub.action_routes import Routes, safe_url

class BrowserRouteContextTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name);self.root=root
  self.store=Store(root/'hub.sqlite3');Conversations(self.store)
  with self.store.connect() as db:
   db.execute('INSERT INTO projects VALUES(?,?,?)',('p1','project',str(root)))
   db.execute('INSERT INTO chats(id,project_id,title,created) VALUES(?,?,?,?)',('c1','p1','chat',now()))
  self.svc=Routes(self.store,FileLibrary(root/'state',root/'files'),root/'artifacts')
 def tearDown(self):self.tmp.cleanup()
 def route(self):
  return {'title':'Route','start_url':'https://someone:password@example.com/landing?token=secret#frag','steps':[{'title':'Click','before_url':'https://example.com/landing?token=a','after_url':'https://example.com/next?token=b','instruction':'Press go'}]}
 def test_input_sanitized_editor_and_prepare(self):
  route=self.svc.save('c1',self.route())
  self.assertEqual(route['start_url'],'https://example.com/landing')
  self.assertEqual(route['steps'][0]['before_url'],'https://example.com/landing')
  self.assertEqual(route['steps'][0]['after_url'],'https://example.com/next')
  prepared=self.svc.prepare('c1',route['id'])
  self.assertTrue(prepared['ready']);self.assertEqual(prepared['start_url'],route['start_url'])
  self.assertFalse('password' in json.dumps(prepared))
  self.assertIn('never',prepared['recovery'])
 def test_reject_unsafe_url(self):
  broken=self.route();broken['start_url']='javascript:alert(1)'
  with self.assertRaises(ValueError):self.svc.save('c1',broken)
  broken=self.route();broken['steps'][0]['after_url']='file:///C:/secret'
  with self.assertRaises(ValueError):self.svc.save('c1',broken)
  self.assertEqual(safe_url('https://u:p@example.com:8443/a?key=x#x'),'https://example.com:8443/a')
 def test_learning_url_chain_and_historical_links(self):
  task=self.store.create('goal',str(self.root),'browser','r1',[])
  with self.store.connect() as db:db.execute('INSERT INTO chat_tasks VALUES(?,?,?)',('c1',task['id'],0))
  obs={'id':'ob1','url':'https://example.com/start?private=1','title':'Start','elements':[],'page_signature':'a'}
  aid=self.store.begin_action(task['id'],'browser_navigate',{'url':'https://example.com/start?private=1'})
  self.store.end_action(aid,{'input_sent':True,'after':obs})
  aid2=self.store.begin_action(task['id'],'browser_act',{'action':'click','observation_id':'ob1'})
  self.store.end_action(aid2,{'input_sent':True,'after':{'id':'ob2','url':'https://example.com/done?token=b','title':'Done','elements':[],'page_signature':'b'}})
  self.store.update(task['id'],state='waiting_review')
  route=self.svc.learn('c1',task['id'],'Imported')
  self.assertEqual(route['start_url'],'https://example.com/start')
  self.assertEqual(route['steps'][1]['before_url'],'https://example.com/start')
  self.assertEqual(route['steps'][1]['after_url'],'https://example.com/done')
  self.assertEqual(route['steps'][1]['evidence'][0]['url'],'https://example.com/start')
  self.assertNotIn('private=1',json.dumps(route))
 def test_resume_is_read_only_not_replay_and_chat_scoped(self):
  route=self.svc.save('c1',self.route());task=self.store.create('route',str(self.root),'browser','run1',[])
  with self.store.connect() as db:
   db.execute('INSERT INTO chat_tasks VALUES(?,?,?)',('c1',task['id'],0))
   db.execute('INSERT INTO action_route_runs VALUES(?,?,?,?,?)',(route['id'],'c1',task['id'],route['revision'],now()))
  aid=self.store.begin_action(task['id'],'browser_navigate',{'url':'https://example.com/start'})
  self.store.end_action(aid,{'input_sent':True,'after':{'id':'ob1','url':'https://example.com/start?a=b'}})
  uncertain=self.store.begin_action(task['id'],'browser_act',{'action':'click'})
  before=len(self.store.actions(task['id']))
  result=self.svc.resume('c1',route['id'],task['id'])
  self.assertEqual(result['last_observed_url'],'https://example.com/start')
  self.assertFalse(result['safe_to_auto_replay'])
  self.assertTrue(result['requires_fresh_browser_observation'])
  self.assertIn(uncertain,result['pending_action_ids'])
  self.assertEqual(len(self.store.actions(task['id'])),before)
  self.assertEqual(self.svc.runs('c1',route['id'])['runs'][0]['task_id'],task['id'])
  with self.assertRaises(KeyError):self.svc.resume('c1',route['id'],'other')
 def test_editor_has_start_urls_history_and_source_links(self):
  editor=(Path(__file__).parent.parent/'hub'/'static'/'action-routes.js').read_text(encoding='utf-8')
  for expected in ('כתובת דף ההתחלה','כתובת לפני הפעולה','כתובת אחרי הפעולה',"'runs'","'resume'",'פתח כתובת מקור היסטורית'):
   self.assertIn(expected,editor)

 def test_http_editor_save_run_and_reconnect_is_journal_only(self):
  from fastapi import FastAPI
  from fastapi.testclient import TestClient
  from hub.action_routes import router
  class DummyEngine:
   def __init__(self):self.enqueued=[]
   def enqueue(self,task_id):self.enqueued.append(task_id)
  engine=DummyEngine();app=FastAPI();app.include_router(router(self.store,engine))
  client=TestClient(app)
  created=client.post('/api/chats/c1/action-routes',json={'action':'create','body':self.route()}).json()
  assert created['start_url']=='https://example.com/landing'
  rid=created['id']
  prepared=client.post('/api/chats/c1/action-routes',json={'action':'prepare','route_id':rid}).json()
  assert prepared['start_url']=='https://example.com/landing'
  result=client.post('/api/chats/c1/action-routes',json={'action':'run','route_id':rid,'request_id':'route-context-integration-test'}).json()
  assert result['task_id'] in engine.enqueued
  aid=self.store.begin_action(result['task_id'],'browser_navigate',{'url':'https://example.com/next'})
  self.store.end_action(aid,{'after':{'id':'ob-2','url':'https://example.com/next?private=1'},'input_sent':True})
  task_id=result['task_id']
  # A brand-new Routes service (as in a later request / restarted UI)
  # can recover the route/run association without repeating actions.
  response=client.post('/api/chats/c1/action-routes',json={'action':'runs','route_id':rid}).json()
  assert response['runs'][0]['task_id']==task_id
  actions_count=len(self.store.actions(task_id))
  resumed=client.post('/api/chats/c1/action-routes',json={'action':'resume','route_id':rid,'task_id':task_id}).json()
  assert resumed['last_observed_url']=='https://example.com/next'
  assert resumed['safe_to_auto_replay'] is False
  assert len(self.store.actions(task_id))==actions_count
