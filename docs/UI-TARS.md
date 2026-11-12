# UI-TARS browser driver

## 0.26.0 — Local UI-TARS browser driver — 2026-11-12

Installed optional UI-TARS 1.5 7B Q4_K_M browser driver using a local llama.cpp OpenAI-compatible runtime. Existing normal/code model choice, task runner, permissions, source-bound screenshots, current DOM targeting, cancellation, uncertain-action fencing and entity-bound completion remain authoritative. No new Python dependency or data migration. Includes compact browser decision evidence, native/web routing corrections and desktop-tool disclosure from the preceding browser effectiveness candidate.

Controls: Settings > local model > browser driver; select UI-TARS local. MCP model_settings_status/model_settings_command use the same persisted browser_driver field and validation. Browser-runtime availability is separate from the primary Ollama model's loaded state. Local runtime is installed in E:/AI/tools/ui-tars-local and requires start-gpu.cmd; automatic startup is not implemented.

Actual failures fixed: screenshot coordinates returned inside ref; duplicate historical tool-evidence text inflating packets after old images were removed; copied browser_act syntax and stale observation identifiers. Translation validates current targets; stale identifiers remain rejected. A malformed proposal gets at most one model correction before any input is sent, and both calls count toward usage.

Deployed agent-owned acceptance e38baed90ee24990bcaf2b586f077237 completed navigation, English Continue, Russian Продолжить, Hebrew שמור and exact fresh outcome verification "Orion saved successfully" without external feedback or manual steps. Browser assessment recorded verified=true, fresh_operation_verified=true and entity_verified=true. Final protocol candidate0124139271034caba0d7a0215a609a17 revision1 passed19 focused tests; update946da71bcca142ccb5f6122a291f49d7 ACTIVE_VERIFIED. This is one disposable multi-screen workflow, not a broad multilingual/site benchmark.

Successful task:8844 input/105 output tokens across5 model calls, approximately30 seconds from task creation to final assessment. Four visual inference request round trips total8.734 seconds; the fifth text assessment latency is not separately recorded. All five development acceptance attempts, including four failures, total30642 input/250 output tokens across14 calls. Diagnostic proposal-only replays are separate from these task totals. No comparable Qwen run or general speedup claim. Accounting remains estimated before inference and measured from provider usage after inference.

Runtime readback: ui-tars-local available; Ollama models=[] (Qwen weights retained, unloaded); GPU7150/8192 MiB at sampled post-run check. Preserve headroom: normal/code tasks can still load their primary model; automatic cross-runtime VRAM arbitration is not implemented.

Limitations: browser-only; visual points must map to current DOM controls, so canvas-only targets/arbitrary desktop gestures are unsupported. External-feedback mode, real-account login, downloads, broad-site reliability and reboot/autostart not validated in this release. Unsupported or over-budget tasks fail explicitly. No human-level autonomy claim.

Deployed parity update71a6fd237ee94517925e87da2959403b is ACTIVE_VERIFIED; seven focused parity/protocol/packet tests passed. Native Qt settings were refreshed and showed UI-TARS selected/active plus primary model unloaded. Installed registered MCP status/get handlers returned the same saved/effective selection and runtime availability. The current ChatGPT cached catalog does not expose those newer tool names, so this is installed-handler verification, not an external ChatGPT invocation.

Release packaging:32 focused tests passed from the clean0.26.0 release worktree; git diff --check passed. Provider source matches deployed behavior (one whitespace-only line normalized with AST equality).

Evidence: E:/AI/artifacts/ui-tars-acceptance-20261112/acceptance-results.json, task action log, runtime install manifest/SHA receipt in E:/AI/tools/ui-tars-local. Existing chats/projects/skills/permissions/browser profile retained; no history deletion.

Rollback: switch browser_driver to default through UI or MCP; no schema downgrade or model deletion. Stop only the owned UI-TARS runtime when no browser task is active before loading another GPU model. For code rollback use a reviewed reverse candidate and the existing Guard workflow; do not restore the task database. Physical rollback/reboot are not claimed.
