import tempfile,unittest
from pathlib import Path
from PIL import Image
from hub.store import Store,Conflict,now
from hub.conversations import Conversations
from hub.file_library import FileLibrary
from hub.action_routes import Routes
class RoutesTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.store=Store(self.root/'hub.sqlite3');Conversations(self.store)
  with self.store.connect() as db:
   for p in ('p1','p2'):db.execute('INSERT INTO projects VALUES(?,?,?)',(p,p,str(self.root/p)))
   for c,p in [('c1','p1'),('c2','p1'),('c3','p2')]:db.execute('INSERT INTO chats(id,project_id,title,created) VALUES(?,?,?,?)',(c,p,c,now()))
  self.library=FileLibrary(self.root/'state',self.root/'files')
  self.service=Routes(self.store,self.library,self.root/'artifacts')
 def tearDown(self):self.tmp.cleanup()
 def body(self):
  return {'title':'Connect channel','parameters':[{'name':'channel','label':'Channel'}],'steps':[{'title':'Choose','instruction':'Select {{channel}}','success':'Connected {{channel}}'}]}
 def test_scope_and_revision(self):
  r=self.service.save('c1',self.body())
  with self.assertRaises(KeyError):self.service.get('c2',r['id'])
  with self.assertRaises(ValueError):self.service.save('c1',r,r['id'],1,'project')
  r=self.service.save('c1',r,r['id'],1,'project',True)
  self.assertEqual(self.service.get('c2',r['id'])['title'],'Connect channel')
  with self.assertRaises(KeyError):self.service.get('c3',r['id'])
  with self.assertRaises(Conflict):self.service.save('c1',r,r['id'],1,'project')
  with self.assertRaises(ValueError):self.service.save('c2',r,r['id'],2,'project')
  self.service.delete('c1',r['id'],2)
  with self.assertRaises(KeyError):self.service.prepare('c1',r['id'],{'channel':'Other'})
 def test_parameters_and_no_execution(self):
  r=self.service.save('c1',self.body())
  self.assertFalse(self.service.prepare('c1',r['id'])['ready'])
  a=self.service.prepare('c1',r['id'],{'channel':'לוגיק פרו'})
  self.assertEqual(a['steps'][0]['instruction'],'Select לוגיק פרו')
  self.assertEqual(self.store.list(),[])
  with self.assertRaises(ValueError):self.service.prepare('c1',r['id'],{'account':'other'})
 def test_image_reference_and_hash(self):
  f=self.library.reserve('reference.png','test','image/png');Image.new('RGB',(50,50),'red').save(f['path']);self.library.finish(f['id'])
  b=self.body();b['steps'][0]['images']=[{'file_id':f['id'],'caption':'Expected screen'}]
  r=self.service.save('c1',b)
  self.assertEqual(self.service.image('c1',r['id'],r['steps'][0]['id'],0,'reference'),Path(f['path']))
  Image.new('RGB',(50,50),'blue').save(f['path'])
  with self.assertRaises(Conflict):self.service.image('c1',r['id'],r['steps'][0]['id'],0,'reference')
 def test_no_forged_evidence(self):
  b=self.body();b['verification']='verified';b['steps'][0]['evidence']=[{'task_id':'private'}]
  r=self.service.save('c1',b)
  self.assertEqual(r['verification'],'draft');self.assertEqual(r['steps'][0]['evidence'],[])
 def test_learn_actual_actions_without_replay(self):
  task=self.store.create('goal',str(self.root),'browser','task',[])
  with self.store.connect() as db:db.execute('INSERT INTO chat_tasks VALUES(?,?,?)',('c1',task['id'],0))
  p={'id':'o1','title':'Choose channel','elements':[{'ref':'e1','name':'Example'}],'page_signature':'one'}
  aid=self.store.begin_action(task['id'],'browser_observe',{});self.store.end_action(aid,p)
  aid=self.store.begin_action(task['id'],'browser_act',{'action':'click','ref':'e1','observation_id':'o1'});self.store.end_action(aid,{'input_sent':True,'after':{'id':'o2','title':'Connected','elements':[]}})
  self.store.update(task['id'],state='waiting_review')
  r=self.service.learn('c1',task['id'],'Remember')
  self.assertEqual(len(r['steps']),1);self.assertIn('Example',r['steps'][0]['instruction'])
  self.assertEqual(r['verification'],'historical_unverified');self.assertEqual(len(self.store.actions(task['id'])),2)
  with self.assertRaises(ValueError):self.service.learn('c2',task['id'],'Wrong scope')
if __name__=='__main__':unittest.main()
