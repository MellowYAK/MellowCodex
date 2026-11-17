# Windows startup recovery — 2026-11-18
Status: implementation and live registration verified; cold-boot and complete stop/start acceptance pending. Not a stable installer release.

## Contract
The Windows-managed, protected OwnerBroker remains separate. Hub, MCP Gateway and Desktop must run with the ordinary interactive token. The old administrator alignment and duplicate fallback launch paths have been removed from start.ps1. Startup now uses the existing ownership-checked reconciler and verifies the real pair and broker before reporting ready.

## Installation and shortcuts
install-startup.ps1 is the finalization step after the pinned dependencies and protected Guard/OwnerBroker have been installed by the supported owner workflow. It verifies the ordinary user and broker, registers the user logon preference and periodic recovery task as Limited/Interactive, and creates MellowCodex - Start, Stop and Status on the user's desktop. The source installer invokes this finalization. Existing installations may run it as the ordinary user. It does not grant permissions or change the protected broker. The current source packaging still assumes E:\AI and is not a portable EXE installer.
The Stop shortcut asks for confirmation, uses the existing all-service ownership and task preflights, and never kills an unverified process. If successful, its pause lasts through the current Windows boot. When start-with-Windows is enabled, only explicit previous-boot shortcut stop markers expire. Explicit persistent, malformed and disabled-startup markers remain respected.

## Observed on reference computer
- Original direct-MCP recovery checkpoint: ecbfaab834612a952bf04f97c4ef87045eb2fc15; exact PowerShell/file write/execute completed without local inference.
- Both scheduled tasks were disabled even though startup preference was true. Registration now reads Ready, Limited, Interactive; startup preference and effective state agree.
- Three desktop shortcuts created and read back; RunAsUser flag false.
- Existing Hub/Gateway listener ownership verified, both elevated=false; protected OwnerBroker identity verified.
- PowerShell parser and Python compilation passed. Focused boot/ownership tests: 14 passed.
- Full stop attempted by the owner: preflight refused the existing legacy elevated Guard listener because its working directory could not be verified by the ordinary executor. No service was changed. This is not a successful stop test. Do not weaken verification or force-kill the listener.

## One-time migration and acceptance
Use Windows Start menu > Power > Restart (not the Codex Stop shortcut) to retire the old elevated processes. Sign in normally. The two registered Limited tasks should launch/reconcile the stack. Confirm live service identities, broker authentication and direct MCP PowerShell/write execution without inference. Then verify Stop and Start through the desktop shortcuts, followed by a real reboot after a successful Stop. Only after observed full acceptance should a stable release tag be published.
If a foreign or unverifiable process occupies a port, preserve it and diagnose the exact blocker. Do not change Yak, Guard source, protected owner policy, credentials or permissions to force the test.

## Distribution requirements still open
A fresh-machine installer must bundle or provision pinned dependencies and supported protected packages, separate elevated native setup from ordinary user finalization, remove the fixed-drive assumption, support uninstall/upgrade, and pass clean Windows VM install and reboot acceptance. This checkpoint does not claim those requirements have been met.
