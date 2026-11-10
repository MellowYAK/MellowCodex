"""Read-only parameterized machine resource snapshot."""
import json,sys
from pathlib import Path
from datetime import datetime,timezone
import psutil
VALID={"cpu","memory","disk","process_count"}
def snapshot(args):
    if not isinstance(args,dict) or set(args)-{"sections","disk_path"}: raise ValueError("Expected sections and optional disk_path only")
    ss=args.get("sections")
    if not isinstance(ss,list) or not 1<=len(ss)<=4 or len(set(map(str,ss)))!=len(ss) or any(not isinstance(s,str) or s not in VALID for s in ss): raise ValueError("Invalid unique sections")
    if "disk_path" in args and "disk" not in ss: raise ValueError("disk_path requires disk")
    if "disk_path" in args and (not isinstance(args["disk_path"],str) or not Path(args["disk_path"]).is_absolute() or not Path(args["disk_path"]).exists()): raise ValueError("disk_path must be existing absolute path")
    d={}
    if "cpu" in ss: d["cpu"]={"logical_cores":psutil.cpu_count(),"physical_cores":psutil.cpu_count(logical=False),"percent_sample":psutil.cpu_percent(interval=.05)}
    if "memory" in ss:
        v=psutil.virtual_memory();d["memory"]={"total_bytes":v.total,"available_bytes":v.available,"used_bytes":v.used,"percent":v.percent}
    if "disk" in ss:
        p=args.get("disk_path",str(Path.home().anchor));v=psutil.disk_usage(p);d["disk"]={"path":p,"total_bytes":v.total,"free_bytes":v.free,"used_bytes":v.used,"percent":v.percent}
    if "process_count" in ss:d["process_count"]={"count":len(psutil.pids())}
    return {"verified":True,"skill":"system_resource_snapshot","backend":"psutil","backend_version":psutil.__version__,"timestamp_utc":datetime.now(timezone.utc).isoformat(),"sections":ss,"data":d}
if __name__=="__main__":
    try:print(json.dumps(snapshot(json.load(sys.stdin))))
    except Exception as exc:
        print(json.dumps({"verified":False,"error":str(exc),"error_type":type(exc).__name__}),file=sys.stderr);sys.exit(1)
