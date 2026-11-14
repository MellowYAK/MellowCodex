# Guard takeover deployment preflight, 2026-11-13

State: BLOCKED before destructive activation; Hub and MCP transports deliberately kept live.

## Evidence
- Installed Guard release: 0.1.1-ef91a6a0d0706d91.
- Guard status: healthy=true, observed_healthy=true, supervisor_healthy=false, started_pids=[]; verified existing Hub pair.
- GuardCore creates OwnedServices(config) with in-memory started and _started_birth lists. Guard MCP server constructs its own GuardCore(config). A Guard activation/restart launched through a different control-plane process cannot reliably populate this existing MCP server instance's started list; status after the restart would still lack verified supervisor provenance. The current release needs persistent, cryptographically or OS-identity-validated start provenance or a supervisor daemon owning the pair and exposing its actual status.
- Guard prepare/approve/activate supports atomic Hub file updates and rollback but only allows installed Hub paths. It cannot patch the installed Guard supervisor release.
- Worktree contains unrelated active changes; do not deploy entire checkout.
- Windows Scheduled Task MellowCodex Service Recovery is enabled, LastTaskResult=0; recovery script recover-mcp-connection.ps1 check-only succeeded. This is local recovery, not automatic external OAuth consent.

## Safe next steps
1. Produce an isolated Guard release candidate changing OwnedServices status semantics to load durable, tamper-resistant PID+creation-time provenance from a Guard-owned supervisor process, with tests across separate processes and Guard MCP server restarts. Never infer ownership from ports alone.
2. Deploy Guard release using Guard's own approved installer/owner workflow with rollback, not Hub prepare allowlist. Preserve existing auth/OAuth, relay and user work.
3. Only when all active tasks are idle, use authorized guarded stop/start. Ensure an independent scheduled recovery owner survives the interruption, durable operation receipt and timeout.
4. Verify local Hub/Gateway/Guard/Guard Gateway HTTP, then actual ChatGPT-to-MellowCodex and ChatGPT-to-Guard MCP calls; OAuth may require user consent.
5. Verify health UI live sampling and guard status across separate MCP requests, with supervisor_healthy=true only if provenance verified. Roll back on failed postconditions.

No forced service interruption or false-green state was performed.