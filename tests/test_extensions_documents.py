import asyncio,json
import pytest
from hub.extensions import Extensions
from hub.documents import write_document,inspect_document

def test_extension_publishes_only_passing_version_and_detects_changes(tmp_path):
    async def run():
        workspace=tmp_path/'workspace';workspace.mkdir()
        (workspace/'source.py').write_text('import json,sys\ndef double(x): return x*2\nif __name__=="__main__": print(double(json.load(sys.stdin)["value"]))')
        (workspace/'test.py').write_text('from tool import double\nassert double(3)==6\nassert double(-4)==-8')
        task={'id':'test','workspace':str(workspace)};registry=Extensions(tmp_path/'registry')
        result=await registry.register(task,'double_number','Double numbers','source.py','test.py')
        assert result['registered']
        assert (await registry.run(task,'double_number',{'value':7}))['stdout'].strip()=='14'
        (workspace/'test.py').write_text('raise ValueError("test fails")')
        assert not (await registry.register(task,'double_number','Broken','source.py','test.py'))['registered']
        assert registry.list()[0]['version']==result['version']
        source=tmp_path/'registry'/'double_number'/result['version']/'tool.py';source.write_text('print("tampered")')
        with pytest.raises(ValueError,match='changed'):await registry.run(task,'double_number',{})
    asyncio.run(run())

def test_hebrew_word_and_excel_roundtrip_preserve_original(tmp_path):
    from docx import Document
    from docx.oxml.ns import qn
    from openpyxl import load_workbook
    text='בדיקה של Windows 11 ושל Excel במחיר 123.45 ₪'
    doc=tmp_path/'hebrew.docx';book=tmp_path/'hebrew.xlsx'
    write_document(doc,[{'type':'paragraph','text':text}])
    assert inspect_document(doc)['paragraphs']==[text]
    assert Document(doc).paragraphs[0]._p.pPr.find(qn('w:bidi')) is not None
    write_document(book,[{'type':'cell','sheet':'דוח','cell':'A1','value':text},{'type':'cell','sheet':'דוח','cell':'A2','value':'=2+3'}])
    loaded=load_workbook(book);assert loaded['דוח'].sheet_view.rightToLeft
    assert loaded['דוח']['A1'].value==text and loaded['דוח']['A2'].data_type=='s'
    original=doc.read_bytes();changed=tmp_path/'changed.docx'
    write_document(changed,[{'type':'replace_paragraph','index':0,'text':'טקסט חדש with English'}],doc)
    assert original==doc.read_bytes()
    with pytest.raises(ValueError,match='original'):write_document(doc,[])

def test_status_contains_exact_uncertain_tool_reason(tmp_path):
    from hub.store import Store
    from hub.task_status import task_status
    store=Store(tmp_path/'db');t=store.create('close','.', 'desktop','one')
    action=store.begin_action(t['id'],'desktop_action',{'action':'click'})
    store.event(t['id'],'unknown_action',{'action_id':action,'name':'desktop_action','error':'1400 Invalid window handle'})
    store.update(t['id'],state='waiting_user',result='Needs observation')
    report=task_status(store,t['id'])
    assert report['blocked'] and '1400 Invalid window handle' in report['text']
    assert report['diagnostics']['actions'][0]['state']=='pending'
