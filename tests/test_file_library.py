import hashlib
from pathlib import Path
import pytest
from hub.file_library import FileLibrary,safe_name
from hub.attachments import prepare_attachments
from hub.browser_profile import save_tabs,load_tabs


def test_original_audio_survives_reopen_and_becomes_context(tmp_path):
    library=FileLibrary(tmp_path/'state',tmp_path/'files')
    raw=b'RIFF\x00\x00WAVE'+bytes(range(256))
    item=library.import_bytes('../recording.wav',raw,'audio/wav')
    reopened=FileLibrary(tmp_path/'state',tmp_path/'files').get(item['id'],ready=True)
    assert Path(reopened['path']).read_bytes()==raw
    assert reopened['sha256']==hashlib.sha256(raw).hexdigest()
    text,images=prepare_attachments([{'file_id':item['id']}],library=library)
    assert item['path'] in text and 'not been transcribed' in text and not images


def test_download_status_and_same_names_do_not_overwrite(tmp_path):
    library=FileLibrary(tmp_path/'state',tmp_path/'files')
    first=library.reserve('image.png','browser download')
    with pytest.raises(ValueError):library.get(first['id'],ready=True)
    second=library.import_bytes('image.png',b'original')
    assert first['path']!=second['path']
    library.fail(first['id'],'interrupted')
    assert library.get(first['id'])['status']=='failed'
    assert Path(second['path']).read_bytes()==b'original'


def test_windows_filename_containment(tmp_path):
    library=FileLibrary(tmp_path/'state',tmp_path/'files')
    for name in ['../../outside.txt',r'C:\outside\secret.txt','CON','a:stream','..','<bad>?']:
        item=library.reserve(name,'test')
        assert Path(item['path']).resolve().is_relative_to(library.root)
        assert ':' not in item['name'] and '/' not in item['name'] and '\\' not in item['name']


def test_restore_tabs_without_replaying_auth_codes(tmp_path):
    path=tmp_path/'tabs.json'
    save_tabs(path,['https://chatgpt.com/c/123','https://auth.example/callback?code=secret','javascript:alert(1)','https://example.com/?token=secret'],2)
    urls,selected=load_tabs(path)
    assert urls==['https://chatgpt.com/c/123','https://auth.example/','about:blank','https://example.com/']
    assert selected==2 and 'secret' not in path.read_text()
    path.write_text('broken')
    assert load_tabs(path)==([],0)


def test_file_reference_survives_followup_chat(tmp_path,monkeypatch):
    import hub.file_library as module
    from hub.conversations import Conversations
    from hub.store import Store
    library=FileLibrary(tmp_path/'library-state',tmp_path/'files')
    monkeypatch.setattr(module,'FileLibrary',lambda:library)
    item=library.import_bytes('voice.wav',b'RIFF\x00WAVE','audio/wav')
    store=Store(tmp_path/'chat.sqlite3');conversations=Conversations(store)
    project=conversations.project(str(tmp_path));chat=conversations.create(project['id'])
    first=conversations.submit(chat['id'],'Use this recording','desktop','one',[{'file_id':item['id']}])
    store.update(first['id'],state='done',result='File received')
    second=conversations.submit(chat['id'],'Use that same file again','desktop','two')
    assert any(item['id'] in m['content'] and item['name'] in m['content'] for m in second['messages'])
