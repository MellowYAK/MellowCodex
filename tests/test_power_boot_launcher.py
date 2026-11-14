from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from hub import power as p
from hub import service_health as h

@pytest.mark.parametrize('jitter',[0,.000064,-.000064,.005])
def test_same_windows_boot_sampling_jitter(jitter):
    with patch.object(h.psutil,'boot_time',return_value=1794415308.7549868+jitter):
        assert p.same_boot(1794415308.7549868)
@pytest.mark.parametrize('value',[None,True,'123',float('nan'),float('inf'),122.0,124.0])
def test_other_boot_or_invalid_marker_rejected(value):
    with patch.object(h.psutil,'boot_time',return_value=123.0):
        assert not p.same_boot(value)

def process(pid,exe,cwd,args,parent=0,children=()):
    return SimpleNamespace(pid=pid,exe=lambda:str(exe),cwd=lambda:str(cwd),
        cmdline=lambda:args,ppid=lambda:parent,children=lambda:list(children))

def test_temp_cwd_launcher_requires_exact_trusted_child(tmp_path):
    launcher=tmp_path/'venv/pythonw.exe';base=tmp_path/'base/pythonw.exe';source=tmp_path/'source'
    args=['pythonw.exe','-m','hub.desktop_app']
    child=process(2,base,source,args,parent=1)
    parent=process(1,launcher,tmp_path/'temp',args,children=[child])
    assert h.verified_venv_launcher(parent,source.resolve(),{launcher.resolve()},{base.resolve()})
    for bad in [
        process(2,base,tmp_path/'other',args,parent=1),
        process(2,tmp_path/'untrusted.exe',source,args,parent=1),
        process(2,base,source,['pythonw.exe','-m','other'],parent=1),
        process(2,base,source,args,parent=99),
    ]:
        parent.children=lambda:[bad]
        assert not h.verified_venv_launcher(parent,source.resolve(),{launcher.resolve()},{base.resolve()})
    parent.children=lambda:[child]
    assert not h.verified_venv_launcher(parent,source.resolve(),{(tmp_path/'other.exe').resolve()},{base.resolve()})
