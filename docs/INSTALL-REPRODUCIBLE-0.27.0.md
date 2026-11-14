# Reproducible installation: MellowCodex 0.27.0

## Target

- Windows x64, preferably Windows 11, compatible driver/interactive desktop session.
- Current development installation root: `E:\AI`; application checkout: `E:\AI\repos\local-agent-hub`. Scripts presently assume this path. Use a machine with an E: drive or adapt the scripts carefully before running.
- Python 3.12.16, pinned dependencies in `requirements.lock.txt`. External binary releases are pinned by URL and SHA256 in `tools-download-lock.json`: uv 0.13.7, Ollama v0.40.14, OpenCode v1.19.5.
- NVIDIA RTX 3050 8 GiB is the reference tested machine; a GPU and installed NVIDIA drivers are not distributed by Git. Verify model RAM/VRAM needs if hardware differs.

## Checkout and setup

1. In PowerShell (under your own account), prepare `E:\AI\repos` and clone this repository as `E:\AI\repos\local-agent-hub`.
2. Review `download-tools.ps1` and `tools-download-lock.json`. Run the downloader to fetch the three selected Windows x64 archives, verify exact SHA256 and install them into `E:\AI\tools`. It never executes downloaded files and aborts on a hash mismatch.
3. Run `install.ps1` from the repository root. It expects the pinned Python environment and invokes `start.ps1` after dependency synchronization. No elevation/OwnerBroker consent is implicit in the checkout.
4. Pull/configure the intended Ollama model separately; model weights are deliberately not committed. `installation-manifest.json` records a historical `qwen3.5:4b` reference; the model selected in a live task can differ, so check current settings rather than assuming that manifest equals active configuration.
5. Install and configure the separate Mellow Guard 0.1.1-59a4f92505e6775f release through its authorized owner-managed workflow, along with Guard Gateway, OwnerBroker, SSH relay and any chosen OAuth connectors. Neither protected local credentials nor their approvals are portable.
6. Reinstall required versioned skills under `E:\AI\extensions` using owner-approved Shop lifecycle. The repository includes the original `scripts/skills` packages, including `computer_shutdown`, but installed extension manifests and runtime state are separate. Not all 24 installed packages on the reference machine are guaranteed by a fresh checkout.
7. Restore personal configuration, chat history and browser profiles only by deliberate local backup; these private states are excluded from Git.
8. Run focused tests, start the local services, and request a fresh full Health status. Accept only independently verified behavior, not a remembered green badge.

## What Git can reproduce

The committed application code, test suites, documentation, dependency lock, scripts and local Skill Shop source packages. Pinning a repository commit gives exact source files. This does not reproduce Windows scheduled tasks, installed external Guard release, credentials, model bytes, connected accounts, machine-specific device permissions, or running service ownership.

## Known discrepancy

The post-reboot snapshot reports 10/10 local service components operational and both MCP paths reachable, but Guard supervisor provenance remains `supervisor_healthy=false`. Do not reinterpret `healthy=true` as a verified Guard-owned startup. The system can be functional without that ownership proof.

## Verification protocol

- Check `python --version` is 3.12.16 and locked dependency package versions, then execute the focused pytest suites from `tests/`.
- Confirm the full Health report and separately record Guard `healthy`, `observed_healthy`, `supervisor_healthy` and `health_basis`.
- Validate an authenticated ChatGPT -> MellowCodex MCP call and a separate ChatGPT -> Mellow Guard MCP call.
- Run `system_resource_snapshot` safely for installation speed checks. Do not test the power skill by actually shutting down the computer unless the owner explicitly requests it.
- Compare source hashes or Git commit between machines, not just semantic version strings. External bundles have independent SHA256s and versions.

## Security

Never commit `.env`, credentials, key files, SQLite state, logs, browser profiles, saved OAuth tokens or backup archives. They are excluded by `.gitignore`. Owner-gated operations must remain owner-gated on the destination computer; never copy personal owner-policy database to bypass authorization.
