import json
import pytest
from PIL import Image
from hub import browser_selections as module
from hub.conversations import Conversations
from hub.store import Store

class Library:
    def __init__(self,root):self.root=root;self.files={}
    def add(self,key,data,mime):
        path=self.root/key
        if isinstance(data,bytes):path.write_bytes(data)
        else:path.write_text(json.dumps(data),encoding='utf8')
        self.files[key]={'id':key,'name':key+'.json' if mime=='application/json' else key+'.png','path':str(path),'size':path.stat().st_size,'mime':mime}
        return key
    def get(self,key,ready=True):return self.files[key]

@pytest.fixture
def registry(tmp_path,monkeypatch):
    import io
    library=Library(tmp_path);b=io.BytesIO();Image.new('RGB',(20,20),'blue').save(b,format='PNG')
    for i in range(1,4):
        library.add('image'+str(i),b.getvalue(),'image/png')
        library.add('context'+str(i),{'kind':'element','screenshot_file_id':'image'+str(i),'url':'https://example.test/','element':{'tag':'button','css':{'color':'blue'}}},'application/json')
    monkeypatch.setattr(module,'STATE',tmp_path)
    monkeypatch.setattr(module,'FileLibrary',lambda:library)
    monkeypatch.setattr('hub.file_library.FileLibrary',lambda:library)
    return module.Selections(),tmp_path

def test_numbers_names_restart_rename_unknown(registry):
    r,root=registry
    a=r.save('כותרת','image1','context1');b=r.save('Buy button','image2','context2')
    assert a['number']==1 and b['number']==2
    assert r.save('כותרת','image1','context1')['number']==1
    assert [x['number'] for x in module.Selections().resolve('ברכיב מספר 1 שנה צבע וברכיב 2 הגדל טקסט')['selections']]==[1,2]
    assert r.resolve('change Buy button and כותרת')['selections'][0]['number']==1
    with pytest.raises(ValueError):r.resolve('element 10')
    with pytest.raises(ValueError):r.rename(2,'כותרת')
    assert r.rename(2,'Checkout')['number']==2
    assert r.resolve('Buy button')['selections']==[]
    assert r.resolve('#2')['selections'][0]['name']=='Checkout'
    assert r.resolve('Checkout')['selections'][0]['context']['element']['tag']=='button'

def test_real_submission_context(registry):
    r,root=registry;r.save('Heading','image1','context1');r.save('Footer','image2','context2')
    c=Conversations(Store(root/'tasks.sqlite3'));p=c.project(str(root));chat=c.create(p['id'])
    goal='For element 1 use red; for element 2 use green'
    task=c.submit(chat['id'],goal,'inspect','selection-context-test')
    current=task['messages'][-1]
    assert task['goal']==goal
    assert 'Heading' in current['content'] and 'Footer' in current['content']
    assert 'Re-observe' in current['content'] and len(current['images'])==2
    assert c.submit(chat['id'],goal,'inspect','selection-context-test')['id']==task['id']
