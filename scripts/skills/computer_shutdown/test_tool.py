"""Tests that the shutdown skill never initiates power itself."""
import json
from tool import run

p=run({"action":"preview"})
assert p["next_tool"]=="computer_power_preview"
assert p["next_arguments"]=={"action":"shutdown"}
assert p["performed_power_action"] is False
p=run({"action":"request_shutdown"})
assert p["next_tool"]=="computer_power"
assert p["requires_explicit_current_user_authorization"] is True
assert p["performed_power_action"] is False
assert run({"action":"status","operation_id":"op-123"})["next_tool"]=="computer_power_status"
for bad in ({"action":"shutdown_now"},{"action":"request_shutdown","confirm":True},{"action":"status"},{"action":"preview","operation_id":"anything"}):
    try: run(bad)
    except ValueError: pass
    else: raise AssertionError("Unsafe payload accepted: "+repr(bad))
print("PASS safe shutdown skill; no Windows power request issued")
