"""Safe Hebrew/English natural-language model profile commands."""
from __future__ import annotations
import re
import httpx
from .config import OLLAMA, STATE
from .model_placement import (
    PlacementProfile, GlobalPlacementConfig, load_global, save_global,
    load_profile_overrides, save_profile, resolve_profile,
)


def _intent(text: str):
    s=text.strip().lower()
    if not any(word in s for word in (
        "הגדר","קבע","שמור","בחר","טען","שנה","set ","load ","save ",
        "select ","change ","apply ")):
        return None
    global_scope=any(x in s for x in ("גלובל","ברירת מחדל","לכל המודלים","לכולם",
                                      "global","default","all models"))
    percent=re.search(r"(?<!\d)(100|[1-9]?\d)\s*%",s)
    gpu=any(x in s for x in ("gpu","גיפיו","כרטיס גרפי","כרטיס המסך"))
    cpu=any(x in s for x in ("cpu","סיפיו","מעבד בלבד"))
    mode=None
    if percent and gpu:
        mode="percent"
    elif cpu and any(x in s for x in ("בלבד","only")) and not gpu:
        mode="cpu"
    elif gpu and any(x in s for x in ("בלבד","only")):
        mode="gpu"
    elif any(x in s for x in ("אוטומטי","אוטומטית","automatic","auto")) and (gpu or cpu or "חלוקה" in s):
        mode="auto"
    max_tokens=any(x in s for x in ("מקסימום טוקנים","ללא הגבלת טוקנים",
                                     "maximum tokens","unlimited tokens",
                                     "מקסימום הקשר","maximum context"))
    presets={"ביצועים":"gpu_priority","performance":"gpu_priority",
             "איכות":"maximum_quality","quality":"maximum_quality",
             "חסכוני":"memory_saver","memory saver":"memory_saver",
             "cpu only":"cpu_only","אוטומטי":"automatic","automatic":"automatic"}
    preset=next((v for k,v in presets.items() if k in s and any(w in s for w in ("פרופיל","preset"))),None)
    if not mode and not max_tokens and not preset:
        return None
    patch={}
    if mode:
        patch["mode"]=mode
    if mode=="percent":
        patch["gpu_percent"]=int(percent.group(1))
    if max_tokens:
        patch.update(context_mode="maximum",output_mode="maximum")
    load=bool(re.match(r"^(טען\b|load\b)",s))
    return {"global":global_scope,"changes":patch,"preset":preset,"load":load,"text":s}


async def apply(text: str, *, busy=False):
    if not isinstance(text,str) or len(text)>1000:
        return None
    intent=_intent(text)
    if intent is None:
        return None
    if busy:
        return {"handled":True,"accepted":False,"error":"A model task is active; no settings changed"}
    if intent["global"]:
        old=load_global(STATE)
        changes=intent["changes"]
        values=old.model_dump()
        values["defaults"]={**old.defaults.model_dump(),**changes}
        if intent["preset"]:
            values["active_preset"]=intent["preset"]
        policy=GlobalPlacementConfig.model_validate(values)
        save_global(STATE,policy)
        return {"handled":True,"accepted":True,"scope":"global",
                "saved":policy.model_dump(),"applies":"next_model_load"}
    async with httpx.AsyncClient(timeout=8,trust_env=False) as client:
        response=await client.get(OLLAMA+"/api/tags")
        response.raise_for_status()
    models=[m.get("name") for m in response.json().get("models",[]) if m.get("name")]
    s=intent["text"]
    exact=[name for name in models if name.lower() in s]
    if len(exact)==1:
        name=exact[0]
    else:
        # A unique "9B Q8" shorthand may identify an installed GGUF.
        size=re.search(r"(?<!\d)([0-9]+)\s*b\b",s)
        q=re.search(r"\bq(2|3|4|5|6|8)\b",s)
        candidates=[name for name in models
                    if size and size.group(1)+"b" in name.lower()
                    and (not q or ("q"+q.group(1)) in name.lower())]
        if len(candidates)!=1:
            return {"handled":True,"accepted":False,"error":
                    "Specify one exact installed model or an unambiguous size/quantization; no settings changed",
                    "matching_models":candidates}
        name=candidates[0]
    current=load_profile_overrides(STATE).get(name,{})
    current.update(intent["changes"])
    profile=PlacementProfile.model_validate(current)
    save_profile(STATE,name,profile)
    actual,origin=resolve_profile(STATE,name)
    result={"handled":True,"accepted":True,"scope":"model","model":name,
            "saved":actual.model_dump(),"provenance":origin,"applies":"next_model_load"}
    if intent["load"]:
        from .model_memory import control
        try:
            receipt=await control("switch",name)
            result["loaded"]=receipt.get("verified",False)
            result["memory"]=receipt.get("memory")
            if not result["loaded"]:
                result["accepted"]=False
                result["error"]="Saved profile, but model load was not verified"
        except Exception as exc:
            result.update(accepted=False,loaded=False,error="Profile saved, load failed: "+str(exc)[:250])
    return result
