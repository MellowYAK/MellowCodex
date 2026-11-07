import subprocess
import sys
import pytest
from hub.development.ownership import candidate_owner


def test_second_process_cannot_mutate_owned_candidate(tmp_path):
    code='from hub.development.ownership import candidate_owner\nimport sys\nwith candidate_owner(sys.argv[1]): print("owned")'
    with candidate_owner(tmp_path):
        child=subprocess.run([sys.executable,'-c',code,str(tmp_path)],capture_output=True,text=True,timeout=10)
        assert child.returncode!=0 and 'Candidate is busy' in child.stderr
    child=subprocess.run([sys.executable,'-c',code,str(tmp_path)],capture_output=True,text=True,timeout=10)
    assert child.returncode==0 and child.stdout.strip()=='owned'


def test_exception_releases_candidate_owner(tmp_path):
    with pytest.raises(RuntimeError):
        with candidate_owner(tmp_path):raise RuntimeError('test failed')
    with candidate_owner(tmp_path):pass
