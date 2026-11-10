import importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location("skill_tool",Path(__file__).with_name("tool.py"));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
a=m.snapshot({"sections":["cpu","memory"]});assert a["verified"] and set(a["data"])=={"cpu","memory"} and a["data"]["memory"]["total_bytes"]>0
b=m.snapshot({"sections":["process_count"]});assert b["data"]["process_count"]["count"]>=1
try:m.snapshot({"sections":["cpu"],"disk_path":"C:"})
except ValueError:pass
else:raise AssertionError("rejected parameter was accepted")
print("RESOURCE_SKILL_PASS: two distinct inputs, live psutil and invalid-input rejection")
