import json
from hub.guardian.jobs import UpgradeJobs
from hub.guardian.service import atomic


def test_duplicate_request_does_not_launch_second_supervisor(tmp_path,monkeypatch):
    jobs=UpgradeJobs(tmp_path);launches=[]
    monkeypatch.setattr(jobs.guardian,'verify',lambda release:None)
    class Process:
        pid=123
        def create_time(self):return 321
    monkeypatch.setattr('hub.guardian.jobs.psutil.Process',lambda pid:Process())
    monkeypatch.setattr('hub.guardian.jobs.subprocess.Popen',lambda *args,**kw:launches.append((args,kw)) or Process())
    first=jobs.submit('activate','a'*32,'stable')
    assert jobs.submit('activate','a'*32,'stable')['id']==first['id']
    assert len(launches)==1
    assert launches[0][1]['creationflags']
    assert 'LOCAL_AGENT_ROOT' in launches[0][1]['env']
    atomic(jobs.guardian.control/(first['id']+'.result.json'),{'state':'ACTIVE_VERIFIED'})
    assert jobs.status()['requests'][0]['state']=='ACTIVE_VERIFIED'


def test_recovery_reconciles_abandoned_launch_without_replay(tmp_path):
    jobs=UpgradeJobs(tmp_path)
    atomic(jobs.requests/'old.json',{'id':'old','operation':'activate','release_id':'a'*32,'created':1})
    assert jobs.status()['requests'][0]['state']=='launch_outcome_unverified'
    atomic(jobs.requests/'new.json',{'id':'new','operation':'recover','release_id':None,'created':2})
    atomic(jobs.guardian.control/'new.result.json',{'recovered':[],'recovery_verified':True,'active':{'release_id':None,'epoch':0}})
    old=next(j for j in jobs.status()['requests'] if j['id']=='old')
    assert old['state']=='interrupted_reconciled'
