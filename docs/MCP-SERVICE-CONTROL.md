# Health & Recovery (0.21.0)

Open the native top health indicator, Tools > Health and Services, tray menu, or desktop shortcut **Mellow Health and Services**. The standalone entry is `pythonw -m hub.service_health_ui` from the installed repository, and does not depend on Hub or MCP. An already running desktop imports UI code once; launch the offline shortcut for the updated panel without interrupting its browser.

Each row provides Inspect, Start, Stop, Restart and Repair. Unsupported controls are disabled with the dedicated-control reason (Owner Control, Models, recovery task or shell lifecycle). Global controls provide Check all, Repair all, Restart MCP transports, Start all, Stop all and Reset recovery state. Whole-agent stop/restart previews active-task impact and uses the existing graceful controller.

## Evidence and recovery
The canonical `status` is separate from legacy `state`. Process ownership, API response, network families, connector OAuth/external call and supervisor coverage have independent evidence. Guard's authenticated API may be operational while its supervisor did not start the Hub pair. An owned SSH process does not alone prove successful authentication or tunnel forwarding. IPv4/IPv6 probes are TCP reachability samples, not proof of where packets were lost. Unknown, stale and intentionally disabled model states are not outages.

External evidence expires after 120 seconds. A transport operation invalidates affected current evidence while retaining last success. The existing nonce/ack path verifies MellowCodex round trips. `service_health_connector_observation` records a current, actually observed external call for the explicitly named connector; it is attributed to the external director, never inferred from a listener. Guard OAuth failure does not mark MellowCodex disconnected. Local code cannot complete ChatGPT consent; Reconnect opens connector settings with the affected name, without restarting services.

Repair inspects current services, preserves owner-stop markers, leaves healthy or unknown-owned processes alone, and reconciles only absent supported services once. It reports repaired/unchanged/requires_user_action/failed and rechecks without replaying side effects. Network/OAuth problems do not cause healthy-service restart loops. Explicit Start/Restart handles its relevant markers through the existing manager. No router/network/security configuration changes are automatic.

## Reset, parity and diagnostics
Reset previews exact stale operation IDs and the disposable `health-snapshot.json`. It marks verified dead workers interrupted and removes only that cache. It preserves conversations, projects, skills, credentials, permissions, owner-stop markers, logs, durable evidence and work. It never replays uncertain effects. No destructive application reset is offered.

UI and MCP use the same snapshot, submit/action-status backend and validation. Stable request IDs are idempotent; duplicate active clicks return the existing operation. MCP tools expose compact status, actions, operation IDs and results. New tool schemas may require refreshing the ChatGPT connector's cached tool catalog.

Artifacts: `E:/AI/artifacts/health-recovery-20261111`. The existing supervisor keeps changed-file backups and an update journal for runtime rollback; source rollback must use that reviewed file set while services are idle, never a database downgrade or a destructive Git reset. Desktop browser work is not terminated for panel updates.


## Earlier transport validation

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

## Final 0.21.0 verification
Actual controlled transport Stop/Start and offline Windows panel passed; see VALIDATION.md for operation IDs and retained failed-first-attempt evidence. Manual Check all additionally verifies SSH authentication using the installed identity, BatchMode and strict known_hosts, without changing either. Public DNS and forwarded HTTP are checked separately from authenticated MCP. Background refresh does not launch SSH authentication probes. Controller failures expose sanitized reason codes and the retained local log path.

The running desktop/browser was intentionally not terminated; its imported native UI updates at its next launch. Use the standalone desktop shortcut immediately. Full computer/router reboot and Stop all during active work remain unverified.
