import importlib.util
import sys
import types
from pathlib import Path

NAMES=("voice_service","video_gateway","video_panel","video_relay","text_image_service","image_video_service")
state={name:False for name in NAMES}
calls=[]
class FakeManage:
    @staticmethod
    def snapshot():
        return {name:{"running":state[name],"installed":True} for name in NAMES}
    @staticmethod
    def start_selected(names):
        for name in names:
            state[name]=True
            calls.append(("start",name))
        return {name:"started" for name in names}
    @staticmethod
    def control_one(name,action):
        assert action=="stop"
        state[name]=False
        calls.append(("stop",name))

fake=types.ModuleType("ember_video")
fake.manage=FakeManage
sys.modules["ember_video"]=fake
spec=importlib.util.spec_from_file_location("skill_tool",Path(__file__).with_name("tool.py"))
skill=importlib.util.module_from_spec(spec)
spec.loader.exec_module(skill)

assert skill.main({"action":"status","target":"standard"})["ok"]
assert calls==[]
start=skill.main({"action":"start"})
assert start["ok"] and start["target"]=="standard"
assert len(calls)==4 and not state["text_image_service"] and not state["image_video_service"]
stop=skill.main({"action":"stop","target":"standard"})
assert stop["ok"] and all(not state[n] for n in skill.STANDARD)
assert len(calls)==8
restart=skill.main({"action":"restart","target":"standard"})
assert restart["ok"] and len(calls)==16
assert all(state[n] for n in skill.STANDARD)
assert skill.main({"action":"status","target":"all"})["ok"]
for invalid in ({"action":"unknown"},{"action":"start","target":"evil"},{"action":"status","extra":1},[]):
    try:
        skill.main(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid request accepted: "+repr(invalid))
print("TESTS_OK: status/start/stop/restart/default/optional/invalid")
