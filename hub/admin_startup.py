"""Windows runtime identity contract. Never elevate or terminate an executor."""
import ctypes
import os
import json
import sys

def elevated(pid):
    import win32api, win32con, win32security
    process = win32api.OpenProcess(0x1000, False, pid)
    try:
        token = win32security.OpenProcessToken(process, win32con.TOKEN_QUERY)
        try:
            return bool(win32security.GetTokenInformation(token, win32security.TokenElevation))
        finally:
            token.Close()
    finally:
        process.Close()

def require_standard_user(component="MellowCodex"):
    if os.name != "nt":
        return
    if ctypes.windll.shell32.IsUserAnAdmin() or elevated(os.getpid()):
        raise RuntimeError(component + " must run as your ordinary Windows user. Close the administrator window and use MellowCodex Start. The protected OwnerBroker remains separate.")

def check_pair(require_running=False, verify_broker=False):
    require_standard_user()
    from . import service_health as h
    cfg = h.config()
    inventory = h.inventory()
    result = {}
    for name, port in (("hub", int(cfg.get("hub_port", h.PORT))), ("gateway", int(cfg.get("gateway_port", 8897)))):
        opened, pids = h.port_identity(port)
        owned = {p["pid"] for p in inventory.get(name, []) if p["owned"]}
        if not opened:
            if require_running:
                raise RuntimeError(name + " is not listening; inspect MellowCodex service health.")
            result[name] = {"running": False}
            continue
        if not pids or not pids.issubset(owned):
            raise RuntimeError(name + " listener ownership is unverified; no process will be replaced.")
        if os.name == "nt" and any(elevated(pid) for pid in pids):
            raise RuntimeError(name + " is running elevated. Stop the owned services with the recovery controller, then launch MellowCodex Start normally.")
        result[name] = {"running": True, "pids": sorted(pids), "elevated": False}
    if verify_broker:
        from .owner_broker import owner_status
        status = owner_status()
        result["owner_broker_verified"] = status.get("server_identity_verified") is True
        if not result["owner_broker_verified"]:
            raise RuntimeError("Protected OwnerBroker authentication failed. Check the owner setup/service from the ordinary user session; no permission policy was changed.")
    return result

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--existing"
    if mode not in ("--existing", "--ready", "--launcher"):
        raise SystemExit("Unsupported startup check")
    require_standard_user()
    if mode == "--launcher":
        print(json.dumps({"ordinary_user": True}))
    else:
        print(json.dumps(check_pair(require_running=mode == "--ready", verify_broker=mode == "--ready")))

if __name__ == "__main__":
    main()
