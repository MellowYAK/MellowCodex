from types import SimpleNamespace as S
from hub.guardian.control_plane import listener_owners

def connection(pid,status='LISTEN'):
    return S(pid=pid,status=status,raddr=(),laddr=S(port=8876))

def test_unknown_pid_does_not_overwrite_real_owner_in_either_order():
    real=connection(123,'NONE');unknown=connection(0)
    assert listener_owners([real,unknown],[8876])=={8876:{123}}
    assert listener_owners([unknown,real],[8876])=={8876:{123}}

def test_all_known_owners_are_retained_for_verification():
    assert listener_owners([connection(123),connection(456)],[8876])=={8876:{123,456}}
    assert listener_owners([connection(0)],[8876])=={}
