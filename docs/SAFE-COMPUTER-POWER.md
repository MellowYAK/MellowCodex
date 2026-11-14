## 0.22.0 — Safe computer power and Windows startup — 2026-11-11

Tracked task: 4bc1b4b13f6641d8abf8dbe1c10d4ff7. Runtime deployment 908598faa17a4192bb42251f7edd499b: ACTIVE_VERIFIED. No new dependencies or database migration.

Added computer Shutdown and Restart, distinct from Stop agent services. The durable existing service controller admits one operation, records progress and dispatch intent, drains Ember through its existing busy/ownership-aware manager, gracefully drains Hub tasks/terminals/downloads and managed models, stops owned MCP/Guard/SSH/Ollama services, closes the owned desktop, and only then requests Windows power. Failed or unverified stops block the Windows request. Windows uses /t 0 without /f; unrelated apps are not force-closed. Uncertain power requests are never automatically replayed.

Added one revisioned startup preference shared by UI, native/offline controls and MCP. The current-user Limited logon task starts the managed agent stack and desktop; optional Ember image models are not started. Automatic recovery respects disabled startup on a new boot, preserves owner-stop markers, and can continue recovery in an explicitly started current session. Startup changes do not stop running services or grant owner permissions.

Controls: Settings > General > Windows startup and computer power; Health & Services offline desktop entry; top health indicator, Tools and tray menus in a newly opened shell. Existing desktop/browser was preserved, so already-running native menus load the update only when the shell is reopened. Ordinary local-chat tools and five MCP tools use the same backend; native tool authorization retains the existing owner gate.

Verified: 23 focused regressions; real Ember preview (four standard services running, two extended stopped); deployed registered MCP handlers against HTTP; startup disable/enable with Windows task readback (final enabled, revision 2); stale revision and unconfirmed power rejected with HTTP 409; actual Windows native and deployed web controls, both restart confirmations cancelled before dispatch. External MellowCodex MCP continued working after deployment. Evidence: E:/AI/artifacts/safe-power-20261111/deployed-settings-readback.json and deployed-ui-readback.json; screenshots alongside. Candidate test receipt: 6289f8b84c464414bc3f4f4b44cfa20e/test-f39f1b4ae8654d23a09ad4626994d3ee.json.

Limits: no physical shutdown, reboot or subsequent Windows logon was performed. Full safe-drain order and failure gates were tested with effect sinks isolated; actual full Ember/agent drain was not performed during this release because live work was preserved. Local generation-model natural-language selection was not exercised (inference remains intentionally disabled); tool visibility, authorization classification, dispatch and UI paths were verified. ChatGPT may need connector tool refresh to see newly advertised tools. A Windows accepted request is recorded as windows_requested, never as physical completion. If Windows is cancelled by an unrelated app, inspect the durable operation and explicitly recover services; no automatic repeat of the power request.

Rollback: first disable the new logon task through the shared startup setting while 0.22.0 is running. Prepare an isolated candidate from the prior release 742efe5179a356516c029d39fdeee41440729b10 and deploy through the existing Guard reviewed workflow, restoring only changed source files from the update backups if needed. Retain state, operation journals and all user data; do not downgrade/delete databases. The older recovery scheduler follows the older startup behavior. Do not treat activate_update(recover=true) as an arbitrary rollback API.

## Ordinary-language requests

Examples: "Restart the computer safely", "Shut down the computer safely", "Do not start the agent with Windows", or their Hebrew equivalents. The current request must explicitly authorize computer power, not merely restarting a service. Native chat still obeys owner authorization and requires an enabled generation model to select tools.

MCP: computer_power_preview(action), computer_power(action, request_id, confirm_tasks), computer_power_status(operation_id), agent_startup_status(), agent_startup_set(enabled, expected_revision). Read preview/revision first. Power requires confirm_tasks=true. Stable request IDs and dispatch intent prevent uncertain replays.

## State and safety

Power/startup records are under E:/AI/state; service action journals are under service-actions. A transient boot-bound power marker pauses recovery without converting a computer restart into a permanent user Stop. Explicit previous per-service stops remain respected. No credentials are written into diagnostics.

The power drain does not terminate unrelated SSH sessions, arbitrary processes or the protected OwnerBroker. Windows manages unrelated services on actual shutdown. User-owned apps may block Windows power because /f is never used. An intentionally unloaded model stays unloaded until requested; logon starts Ollama service, not a forced model inference.
