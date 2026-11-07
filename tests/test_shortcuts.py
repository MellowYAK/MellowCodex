import sys
from types import SimpleNamespace
from hub.shortcuts import shortcut
import pytest

def test_shortcut_readback_and_conflict(tmp_path,monkeypatch):
    target=tmp_path/'app.exe';target.write_bytes(b'test')
    links={}
    class Link:
        def __init__(self,path):self.path=path;self.TargetPath='';self.Arguments='';self.WorkingDirectory=''
        def Save(self):Path(self.path).touch()
    class Shell:
        def SpecialFolders(self,name):return str(tmp_path)
        def CreateShortcut(self,path):return links.setdefault(path,Link(path))
    from pathlib import Path
    client=SimpleNamespace(Dispatch=lambda _:Shell())
    monkeypatch.setitem(sys.modules,'pythoncom',SimpleNamespace(CoInitialize=lambda:None,CoUninitialize=lambda:None))
    monkeypatch.setitem(sys.modules,'win32com',SimpleNamespace(client=client))
    monkeypatch.setitem(sys.modules,'win32com.client',client)
    assert shortcut('create','Example',str(target))['verified']
    assert shortcut('create','Example',str(target))['verified']
    assert shortcut('inspect','Example')['target']==str(target)
    other=tmp_path/'other.exe';other.write_bytes(b'test')
    with pytest.raises(ValueError,match='overwrite'):shortcut('create','Example',str(other))
    assert shortcut('inspect','Example')['target']==str(target)

def test_shortcut_rejects_path_traversal():
    with pytest.raises(ValueError):shortcut('create','../other','anything')
