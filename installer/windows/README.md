# MellowCodex 0.27.0 Windows clean-install candidate

This installer preserves the current PySide6 / QtWebEngine desktop and existing Hub, MCP, Guard and Watchdog start/stop semantics. It is not MellowYak or a WebView2 rewrite.

## For a new Windows user

1. On Windows 11 x64, extract the private installer kit locally. A working Internet connection, free storage and an interactive Windows user account are required.
2. Double-click Install-MellowCodex.cmd in the kit root. Follow the 8 numbered stages. Normal application processes should not run elevated.
3. The setup verifies platform and paths, copies only application source, downloads SHA256-locked UV, Ollama and OpenCode, installs Python 3.12.16 and the locked Python environment including Qt/PySide6. It installs Chromium for Playwright if not skipped.
4. Protected setup requires a separate Windows UAC approval for MellowGuard and MellowOwnerBroker. The private OwnerBroker binary was built on the owner's source machine and is NOT Authenticode-signed. It requires a second explicit confirmation: INSTALL UNSIGNED BROKER. Never publish it to GitHub.
5. Setup builds new Windows-specific owner identity, Guard state and credentials. It never imports the original computer's saved chats, tokens, private credentials, SQLite, browser profile or model weights.
6. Setup registers existing Codex owned startup/recovery tasks, then makes desktop shortcuts named MellowCodex Start and MellowCodex Stop. Start delegates to original start.ps1. Stop delegates to original stop.ps1, asks to type STOP, honors process owner checks and the manual-stop/Watchdog policy.
7. Check setup messages and receipts in the target installation's state\installer directory. A protected step failure stops the installer and must never be treated as success.
8. Install any optional AI model later from Ollama. This private kit includes NO local AI model weights. Remote connector, OAuth and SSH relay credentials require separate owner setup.

## Included and excluded

The Git-ready source is Python, PowerShell, UI/source files, dependency lock, config templates, installation scripts, documentation and checksums. The PRIVATE ZIP additionally includes payload/MellowGuard-source-0.1.1-...zip and payload/MellowOwnerBroker-unsigned-native-source.zip, with SHA256 sidecars. These private payloads must never be committed.

The installer does not include preinstalled Python, virtual environments, PySide6 wheels, Node runtimes, downloaded Ollama models, caches, backups, old release archives, current Windows services/credentials/keys, personal SQLite, logs, browser profiles or other user data.

## Advanced: dry-run without any installation

From the extracted kit root:

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\installer\windows\Install-MellowCodex.ps1 -DryRun

A custom destination may be selected with -AgentRoot D:\MellowCodex. Default location is under the current Windows user's LOCALAPPDATA directory, not E:\AI.

## Critical limitations

STATUS: IMPLEMENTED_AND_PARSE_CHECKED; PRIVATE_PAYLOAD_EXPORTED; OWNER_CLEAN_PC_ACCEPTANCE=NOT_TESTED.

This source-only installer was not executed on a fresh Windows PC. Existing MellowCodex contains historic E:\AI path assumptions; setup rewrites the source copy but must be verified end to end by the owner. Unsigned OwnerBroker must be explicitly approved and deserves security review and signing before public distribution.

Do not treat a port opening as proof of MCP, Guard ownership or full application health. Do not attempt to stop live services on the development PC just to test an installer.

## Owner acceptance checklist (NOT TESTED)

- Install on a truly clean Windows 11 x64 PC (no E: required) under intended interactive Windows account.
- Confirm pinned download checks, Python/PySide6 Qt desktop window, Hub+MCP and protected Guard+OwnerBroker readiness.
- Confirm Start/Stop desktop shortcuts. Stop must request STOP, must only stop owned services, and must preserve manual-stop semantics; Start must restore service readiness.
- Reboot, check silent Watchdog and Windows task startup without popping consoles.
- Check guarded permission denial for unauthorized files/services, MCP direct call, browser navigation, skill and optional model acquisition.
- Document any failures using the created installer logs. Final owner acceptance is not assumed.

## GitHub

Commit installer scripts and clean source only; exclude the private payload directory, all archives, binaries, models, venv, caches, logs and user state. Review licenses, secrets and existing uncommitted source modifications before pushing. Private ZIP releases and installer receipts are NOT Git source.