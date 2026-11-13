# Windows startup recovery checkpoint (2026-11-13)

Status: **startup code fixed; live logon-path simulation passed; actual post-reboot verification PENDING**.

## Observed root cause
The Windows account has PowerShell execution policy Restricted. The scheduled recovery task itself already invokes powershell.exe with process-scoped -ExecutionPolicy Bypass, but three Python subprocess call sites in hub/power.py did not: the owned startup-task status/management script, the controlled power-stop script, and the next-logon autostart reconciliation script. This caused an internal script launch failure even when the scheduled task reported success. An old agent-manual-stop marker also blocked automatic reconciliation until explicitly cleared via the authorized Start all action.

## Changes in this checkpoint
- hub/power.py: add process-scoped -ExecutionPolicy Bypass to exactly three owned PowerShell subprocess invocations. No machine-wide policy change.
- repair-mellow-startup.cmd: owner double-click recovery entry point.
- repair-mellow-startup.ps1: invokes authorized reconcile-services.ps1 -Action Start -Service all, checks ports 8876/8897/8898/8896, reports failure.
- Intentional manual-stop semantics remain unchanged. No auto-clearing owner stop markers at logon.

## Evidence before reboot
- Local Agent Hub scheduled logon task: exists, owned, enabled, effective=true, consistent=true.
- Exact next-logon Python path: python.exe -m hub.power --autostart returned state=started and exit code 0.
- Reconcile report: errors=[]; listeners true for 8876, 8897, 8898, 8896, 11434.
- Owner repair script executed successfully, exit code 0, all four MCP/Guard service listeners active.
- Actual Windows restart/login has NOT been performed as part of this checkpoint.

## Next Windows login acceptance
1. Sign in to Windows; do not run the manual repair first.
2. Check Scheduled Task Local Agent Hub LastTaskResult, and MellowCodex Service Recovery LastTaskResult.
3. Confirm ports 8876, 8897, 8898, 8896 and both external MCP round trips.
4. Inspect E:/AI/state/service-reconcile.json (fresh timestamp, errors=[]).
5. Verify no unexpected agent-manual-stop or mcp-manual-stop marker; preserve deliberately set manual stops.
6. If failed, run E:/AI/repos/local-agent-hub/repair-mellow-startup.cmd and retain logs.

## Deferred follow-up (NOT fixed in this checkpoint)
- Guard Supervisor reporting discrepancy: internal health supervisor_healthy=true while direct Guard MCP status supervisor_healthy=false.
- External MCP connection evidence in health UI is stale despite successful live external round trips. Implement trustworthy evidence recording only after next-login acceptance.

This commit intentionally does not claim full all-green health or a verified physical reboot.