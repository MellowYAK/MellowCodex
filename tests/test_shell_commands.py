import subprocess
from hub.shell_commands import prepare
import pytest

@pytest.mark.parametrize('shell,command',[('powershell',"Write-Output 'shell-test'; exit 7"),('cmd','echo shell-test\nexit /b 7')])
def test_real_shell_output_and_exit(tmp_path,shell,command):
    script,argv=prepare(tmp_path,command,shell)
    result=subprocess.run(argv,capture_output=True,timeout=20)
    assert result.returncode==7
    assert b'shell-test' in result.stdout

def test_invalid_shell(tmp_path):
    with pytest.raises(ValueError):prepare(tmp_path,'echo test','other')


def test_nested_powershell_rejected_before_execution():
    from hub.shell_commands import preflight
    assert preflight('powershell -Command "Get-Process | Where-Object {$_.Name}"')['executed'] is False
    assert preflight('Get-Process | Where-Object {$_.Name}') is None
    assert preflight('echo cmd','cmd') is None


def test_empty_result_loop_guard():
    from hub.shell_commands import empty_output_guard
    args={'command':'query'}
    a={'tool':'run_shell','args':args,'state':'complete','result':{'exit_code':0,'output':''}}
    assert empty_output_guard('run_shell',args,[a]) is None
    assert empty_output_guard('run_shell',args,[a,a])['executed'] is False
    assert empty_output_guard('run_shell',{'command':'other'},[a,a]) is None
    assert empty_output_guard('run_shell',args,[a,{**a,'result':{'exit_code':0,'output':'found'}}]) is None
    assert empty_output_guard('run_shell',args,[a,{'tool':'inspect','state':'complete'}]) is None
