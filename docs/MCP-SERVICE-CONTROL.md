# MCP transport control

Desktop shortcuts `Mellow MCP - Start`, `Stop`, `Restart`, and `Status` invoke
`reconcile-services.ps1 -Action ...` with Windows PowerShell 5.1.
Stop pauses the recovery job through a durable owner-stop marker before closing
the signed, owned relay, Guard transport/gateway and Hub MCP gateway. It preserves
Hub tasks, desktop, Ollama and OwnerBroker. Start clears the marker and reconciles;
Restart performs both in sequence. The mutex serializes controls and scheduled recovery.
Do not interpret reachable local ports as verified remote MCP availability.

Recovery probes SSH reachability before spending the installed relay's restart
budget, retains bounded retries and reports the actual relay reason. It checks
the relay again after launch. IPv4 Duplicate conflicts are reported explicitly.
It never changes network configuration automatically.

2026-11-10 actual verification: Stop closed owned MCP processes; Start restored
all five local listeners. Remote verification initially blocked by Windows
reporting a duplicate static Ethernet IPv4 address and SSH connect timeout.
After owner-approved DHCP configuration with a prior local settings backup,
the next scheduled recovery run restored the relay with LastTaskResult 0.
A real MCP model_memory_status call succeeded (selected model present, unloaded).
No full reboot or inference acceptance claimed. Desktop shortcuts installed;
reinstall them with register-mcp-shortcuts.ps1.
These are out-of-band controls usable even when MCP is unavailable.


## Health and service rescue (Hub 0.19.0)

The native top health indicator, Tools > Health and Services, tray menu and offline desktop shortcut open the same local panel. It works without Hub or MCP. The panel and MCP service_health tools submit durable actions to the existing reconcile-services.ps1 manager, with per-service selection, shared locks and intentional-stop markers.

Process presence, verified accepting PID, API response, owned SSH tunnel and remote MCP round-trip evidence are separate. Remote evidence expires after two minutes; use connection_challenge then connection_ack only after actually receiving the nonce through MCP. A local port is never remote proof. OAuth renewal must be done through the MellowCodex connection in ChatGPT when required; reconnect does not bypass consent.

Close window hides the shell. Stop MCP leaves Hub, conversation/tasks, Ollama and the desktop running. Stop all requires task-impact confirmation and uses existing graceful shutdown; the rescue window and protected OwnerBroker stay available. OwnerBroker changes still use existing Owner Control/UAC. Model, recovery-task and shell-specific settings remain in their dedicated controls. No network/credential/permission changes are automated.

Intentional MCP/all/service stop markers persist across reboot. Scheduled Reconcile honors them. Explicit Start/Restart clears the relevant markers, starts dependencies and resumes recovery. Start all clears the global all-stop marker; Start MCP alone does not undo a prior all-services recovery pause. Explicit actions wait up to 30 seconds for the existing manager lock; scheduled recovery remains nonblocking and retries on its existing one-minute schedule. Failed/interrupted jobs are visible and are never replayed automatically.

Native UI/deployment and controlled stop/reconnect validation are recorded separately in VALIDATION.md; no reboot claim is implied.
