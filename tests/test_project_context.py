import json
import os
import pytest
from hub.store import Store
from hub.conversations import Conversations
from hub.context import ProjectContext
from hub.i18n import CapabilityError,catalog

@pytest.fixture
def context(tmp_path):
    root=tmp_path/'project';root.mkdir()
    c=Conversations(Store(tmp_path/'state'/'hub.sqlite3'));p=c.project(str(root))
    return ProjectContext(tmp_path/'state',c),p['id'],root

def test_incremental_search_exact_source_and_stale_handle(context):
    svc,p,root=context
    f=root/'billing.py';f.write_text('def calculate_total(price):\n    return price * 2\n')
    assert svc.refresh(p)['changed']==1
    assert svc.refresh(p)['unchanged']==1
    result=svc.search(p,'calculate_total')['results'][0]
    assert svc.expand(p,result['ref'])['text'].endswith('return price * 2')
    f.write_text('def calculate_total(price):\n    return price * 3\n')
    with pytest.raises(CapabilityError,match='changed'):svc.expand(p,result['ref'])
    svc.refresh(p)
    with pytest.raises(CapabilityError):svc.expand(p,result['ref'])
    f.unlink();assert svc.refresh(p)['deleted']==1
    assert not svc.search(p,'calculate_total')['results']

def test_multilingual_annotations_survive_rebuild(context):
    svc,p,root=context;(root/'settings.py').write_text('value = 42\n')
    svc.refresh(p);svc.annotate(p,'settings.py',['החלפת מודל','смена модели'],['GPU'],must_not_break=['preserve choice'])
    assert svc.search(p,'הַחְלָפַת מודל')['results'][0]['path']=='settings.py'
    assert svc.search(p,'смена')['results'][0]['match_reasons']==['annotation']
    svc.path.unlink();svc=ProjectContext(svc.state,svc.conversations);svc.refresh(p)
    assert svc.search(p,'GPU')['results'][0]['path']=='settings.py'
    assert svc.annotations(p)[0]['payload']['must_not_break']==['preserve choice']

def test_scope_exclusions_and_query_escaping(context,tmp_path):
    svc,p,root=context;(root/'safe.py').write_text('key = 1')
    (root/'.env').write_text('SECRET=do-not-index')
    (root/'state').mkdir();(root/'state'/'private.txt').write_text('do-not-index')
    svc.refresh(p);assert svc.overview(p)['paths']==['safe.py']
    for path in ['../outside.py','C:\\outside.py','safe.py:stream','state/private.txt']:
        with pytest.raises(CapabilityError):svc.annotate(p,path)
    other=root.parent/'other';other.mkdir();(other/'safe.py').write_text('special_unrelated')
    p2=svc.conversations.project(str(other))['id'];svc.refresh(p2)
    assert not svc.search(p,'special_unrelated')['results']
    assert svc.search(p,'" OR * NEAR(')['results']==[]

def test_ast_links_and_apc_idempotent_import(context):
    svc,p,root=context
    (root/'a.py').write_text('import b\ndef run():\n    return b.value\n')
    (root/'b.py').write_text('value=2\n');(root/'test_a.py').write_text('import a\n')
    svc.refresh(p);a=svc.search(p,'run')['results'][0]
    related=svc.related(p,a['ref']);assert {r['kind'] for r in related['related']}=={'imports','tested_by'}
    docs={'documents':[{'doc_id':'source-b','path_or_route':'b.py','keywords':['calculation'],'aliases':['חישוב'],'raw_terms':'calculation backend'}]}
    (root/'apc.json').write_text(json.dumps(docs),encoding='utf-8')
    assert svc.import_apc(p,'apc.json')['imported']==1
    assert svc.import_apc(p,'apc.json')['imported']==1
    assert svc.annotations(p,'b.py')[0]['revision']==1
    assert svc.search(p,'חישוב')['results'][0]['path']=='b.py'

def test_recovery_and_catalog_parity(context):
    svc,p,root=context;c=svc.conversations.create(p)
    task=svc.conversations.submit(c['id'],'Find settings','inspect','request-1')
    recovered=svc.recovery(p)
    assert recovered['recent_tasks'][0]['id']==task['id'] and recovered['replayed'] is False
    assert set(catalog('en'))==set(catalog('ru'))==set(catalog('he'))

def test_preserved_stat_edit_refreshes_source(context):
    svc,p,root=context;f=root/'a.py';f.write_text('value="before"')
    svc.refresh(p);stat=f.stat();f.write_text('value="after!"')
    os.utime(f,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    assert svc.refresh(p)['changed']==1
    assert not svc.search(p,'before')['results']
    assert svc.search(p,'after')['results']


def test_content_hash_reuses_analysis_after_touch_rename_and_syntax_error(context):
    svc,p,root=context;good=root/'good.py';bad=root/'bad.py'
    good.write_text('def present(): return 1');bad.write_text('def broken(')
    calls=[];extractor=svc.extract
    def counted(rel,text):
        calls.append(rel);return extractor(rel,text)
    svc.extract=counted
    svc.refresh(p);assert len(calls)==2;calls.clear()
    stat=good.stat();os.utime(good,ns=(stat.st_atime_ns,stat.st_mtime_ns+1_000_000))
    result=svc.refresh(p)
    assert result['unchanged']==2 and result['changed']==0 and calls==[]
    good.rename(root/'renamed.py');result=svc.refresh(p)
    assert result['changed']==1 and result['deleted']==1 and calls==[]
    assert svc.search(p,'present')['results'][0]['path']=='renamed.py'
    bad.write_text('def repaired(): return 2');svc.refresh(p)
    assert calls==['bad.py']
    assert svc.search(p,'repaired')['results'][0]['path']=='bad.py'
    # Editors/copy tools can preserve both size and timestamps. Only the
    # content digest establishes whether cached analysis is still current.
    calls.clear();renamed=root/'renamed.py';stat=renamed.stat()
    renamed.write_text('def updated(): return 1')
    assert renamed.stat().st_size==stat.st_size
    os.utime(renamed,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    result=svc.refresh(p)
    assert result['changed']==1 and calls==['renamed.py']
    assert svc.search(p,'updated')['results'][0]['path']=='renamed.py'

def test_constraints_survive_optional_note_budget(context):
    svc,p,root=context;(root/'a.py').write_text('value=1')
    svc.refresh(p);svc.annotate(p,'a.py',notes='x'*6000,must_not_break=['preserve signature'])
    data=svc.overview(p)
    assert data['required_constraints'][0]['must_not_break']==['preserve signature']
    assert data['omitted_annotations']==1

def test_missing_root_does_not_erase_index(context):
    svc,p,root=context;f=root/'a.py';f.write_text('value=1');svc.refresh(p)
    moved=root.with_name('moved');root.rename(moved)
    try:
        with pytest.raises(CapabilityError):svc.refresh(p)
        assert svc.overview(p)['paths']==['a.py']
    finally:moved.rename(root)
