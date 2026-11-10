import json,sys
from pathlib import Path
ROOT=Path(r"E:\EmberVideo\app")
sys.path[:0]=[str(ROOT),str(ROOT/"scripts")]
from ember_video import manage
STANDARD=("voice_service","video_gateway","video_panel","video_relay")
EXTENDED=("text_image_service","image_video_service")
GROUPS={"standard":STANDARD,"extended":EXTENDED,"all":STANDARD+EXTENDED}
ORDER=("voice_service","text_image_service","image_video_service","video_relay","video_gateway","video_panel")
def main(q):
 if not isinstance(q,dict) or set(q)-{"action","target"}:raise ValueError("Invalid JSON request")
 a=q.get("action","status");t=q.get("target","all")
 if a not in ("status","start","stop","restart") or t not in set(STANDARD+EXTENDED)|set(GROUPS):raise ValueError("Invalid action or target")
 names=GROUPS.get(t,(t,));steps=[]
 if a in ("stop","restart"):
  for n in ORDER:
   if n in names:
    manage.control_one(n,"stop");steps.append({"service":n,"action":"stop"})
 if a in ("start","restart"):
  result=manage.start_selected(names)
  steps.extend({"service":n,"action":"start","result":v} for n,v in result.items())
 snap=manage.snapshot()
 ok=not any(row.get("result") not in (None,"started") and not (t=="standard" and row["service"]=="video_relay" and row["result"]=="not_installed") for row in steps)
 if a=="stop":ok=ok and all(not snap[n]["running"] for n in names)
 return {"ok":ok,"action":a,"target":t,"steps":steps,"services":{n:snap[n] for n in names}}
if __name__=="__main__":
 try:
  q=json.load(sys.stdin) if len(sys.argv)==1 else {"action":sys.argv[1],"target":sys.argv[2] if len(sys.argv)>2 else "all"}
  response=main(q)
 except Exception as exc:response={"ok":False,"error":type(exc).__name__+": "+str(exc)}
 print(json.dumps(response,ensure_ascii=True))
 sys.exit(0 if response.get("ok") else 1)
