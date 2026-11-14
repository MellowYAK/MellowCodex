# MellowCodex 0.27.0 - Running source snapshot (2026-11-14)

This source snapshot captures the current local application code and install scripts rather than only the final patch. Package metadata remains 0.27.0, matching the running Hub. The snapshot is identified by its Git commit and the tag `v0.27.0-live-20261114`.

## Verified improvements included

- **Bounded-context budget repair.** Adaptive response-token reservation prevents `ContextBudgetError` caused by the configured 16,000-context/16,000-response combination. Actual model `num_predict` follows the computed reservation; project-context bootstrap respects tool scope.
- **SelfDevelop director review.** Required-tool-only steps can return a deterministic, auditable action receipt instead of requiring an unnecessary second model inference; no automatic semantic approval or owner bypass.
- **Skills Shop.** The `computer_shutdown` package was installed using owner-authorized immutable validation; its tool only routes to the built-in safe `computer_power_preview` / `computer_power` / `computer_power_status` tools. It never invokes Windows shutdown directly. One-call `skill_fast_install` and `skill_fast_run` reduce unnecessary model turns, retain immutable tests, hash checks and current owner policy.
- **Guard/Hub services.** Guard ownership was verified in a live pre-shutdown acceptance, and Windows shutdown was accepted through the native power API. After the subsequent boot, the independent full health report marked 10/10 local services operational and authenticated MellowCodex/Guard MCP calls working, but `supervisor_healthy=false` persisted. This is **not** a fully green supervisor.
- **Verification and speed.** Focused fast-path tests passed: 3 fast-path + 3 lifecycle + 4 Shop tests. Baseline direct `extension_run` 116?133ms; isolated Shop commit 107ms. After deployment, isolated fast installs 106?111ms and authenticated one-call skill runs 333?341ms warmed (first call 2.03s). Times were local single-machine samples, not overall chat latency.

## Deployment receipts

- Context budgeting update: `3a28f7a1c4d741a581b7bcd2dd12e0c8` (`ACTIVE_VERIFIED`).
- Skill fast-path update: `f42e6a76caf34c118f2ef64c62249459` (`ACTIVE_VERIFIED`).
- Native Windows shutdown operation: `26c6767620f88eee98ed0b12ba62af18` (queued when observed; actual physical power-off confirmed by the user, not mechanically measured).
- Last health snapshot: 2026-11-14 16:49 +0200, 10/10 locally operational, external MCP connectors answered; Guard supervisor provenance remains unverified after reboot.

## Reproducing the installation

See [Reproducible install](INSTALL-REPRODUCIBLE-0.27.0.md). The repository includes source code, tests, locked Python dependency versions, executable scripts, and a pinned external-tools download manifest. It **does not** include local user data, passwords, OAuth grants, private keys, Windows owner-broker authorization, model weights, GPU drivers, browser profile or the separately installed Guard supervisor release. Those must be installed/configured under the new machine owner's authority. A source clone alone is not proof of identical live behavior on a different machine.

This release snapshot is **not** a clean-install acceptance result. No remote Windows clean-machine test has been performed. In particular, Guard supervisor ownership at startup and real site/browser behavior require further independent verification.
