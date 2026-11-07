import asyncio
from types import SimpleNamespace
import pytest
from hub.native_document import create_document
from hub.errors import ObservationError

def test_locked_session_does_not_open_tab(monkeypatch,tmp_path):
    monkeypatch.setattr('hub.native_document.session_status',lambda:{'interactive':False})
    with pytest.raises(ObservationError,match='no tab or text'):
        asyncio.run(create_document(None,1,'New','text',tmp_path))

def test_nonblank_new_document_never_receives_input(monkeypatch,tmp_path):
    monkeypatch.setattr('hub.native_document.session_status',lambda:{'interactive':True})
    async def inspect(hwnd):return {'id':'before','tab_count':2}
    async def act(args):return {'after_accessibility':{'id':'after','tab_count':3,'elements':[{'type':'Document','enabled':True,'value':'existing work'}]}}
    runner=SimpleNamespace(accessibility=SimpleNamespace(inspect=inspect,act=act))
    with pytest.raises(ObservationError,match='unique blank'):
        asyncio.run(create_document(runner,1,'Add New Tab','text',tmp_path))
