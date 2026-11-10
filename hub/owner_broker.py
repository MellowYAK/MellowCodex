"""Client for the separately installed protected Windows owner service."""
from pathlib import Path
import json
import hashlib
import subprocess
from .owner_policy import Snapshot, Override, Tier
CLIENT = Path(r'C:\ProgramData\MellowOwnerBroker\bin\MellowOwnerClient.exe')

def _call(request=None, chat_id=''):
    if not CLIENT.is_file():
        return {'ok':False,'error':'Protected owner service is not installed'}
    try:
        if hashlib.sha256(CLIENT.read_bytes()).hexdigest() != '5d303edd6e749e1d025cf9f2ab844c19652d69f83ef1986c1f82ab2f4c55e7e2':
            return {'ok':False,'error':'Owner client hash differs from reviewed build'}
        args=[str(CLIENT),'request'] if request is not None else [str(CLIENT),'status','--chat',chat_id]
        result=subprocess.run(args,input=json.dumps(request,sort_keys=True,ensure_ascii=True)+'\n' if request is not None else None,
            capture_output=True,text=True,timeout=5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        data=json.loads(result.stdout)
        if result.returncode or data.get('server_identity_verified') is not True:
            return {'ok':False,'error':'Owner service identity verification failed'}
        return data
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        return {'ok':False,'error':type(exc).__name__}

def owner_status(chat_id=''):
    data=_call(chat_id=chat_id)
    return {**data,'installed':bool(data.get('ok') and data.get('server_identity_verified')),
            'owner_identity_verified':False,
            'owner_grants_enabled':bool(data.get('ok') and data.get('server_identity_verified')),
            'owner_presence_note':'Authenticated service is not proof of a new owner approval.'}

def owner_snapshot(chat_id=''):
    data=_call(chat_id=chat_id)
    if not data.get('ok') or not data.get('server_identity_verified'):
        return Snapshot()
    try:
        overrides={key:Override(Tier(value['tier']),int(value['revision']),value.get('expires_at'))
                   for key,value in data.get('overrides',{}).items()}
        identity=data['install_identity']
        if not isinstance(identity,str) or not identity: return Snapshot()
        return Snapshot(policy_revision=int(data['policy_revision']),default=Tier(data['default']),
                        overrides=overrides,broker_verified=True,
                        broker_install_identity=identity,broker_key_id=identity)
    except (KeyError,TypeError,ValueError):
        return Snapshot()

def authorize_action(request):
    data=_call(request=request)
    if not data.get('ok') or data.get('server_identity_verified') is not True:
        return {'allowed':False,'reason':'owner_broker_unavailable'}
    return data
