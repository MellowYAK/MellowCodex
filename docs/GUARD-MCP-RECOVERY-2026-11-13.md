# Guard Supervisor and MCP recovery checkpoint

Status: code-only checkpoint; not deployed to live Hub; no Guard takeover performed.

- Live Guard status: healthy=true, observed_healthy=true, supervisor_healthy=false, started_pids=[].
- The existing Guard process verifies Hub services that it did not start. A green supervisor ownership badge would be inaccurate until a controlled, authorized Guard-owned startup.
- hub/service_health.py now retains actual supervisor_healthy, observed_healthy, health_basis and accurate provenance rather than mislabeling healthy as supervised.
- recover-mcp-connection.ps1 is a bounded local transport recovery entry point. It honors intentional manual-stop markers, avoids duplicate restart attempts with a 90-second cooldown, writes durable handoff status to E:/AI/state/mcp-recovery-handoff.json and invokes the existing reconciler once. -CheckOnly is read-only for services (writes diagnostic status).
- Existing scheduled Windows recovery task remains enabled and unchanged; no extra watchdog or startup loop was installed.
- Local TCP availability is NOT proof that ChatGPT reconnected. OAuth consent or a remote MCP session cannot be forced locally. Verify with a real external MCP call after any interruption.
- Before controlled takeover: drain all active tasks, prepare Guard-approved candidate, preserve credentials, execute verified stop/start via Guard, verify both external MCP calls and rollback if necessary.
- No Windows reboot, no forced disconnection, no change to owner permissions.