## 0.22.0 — Safe computer power and Windows startup — 2026-11-11

Tracked task: 4bc1b4b13f6641d8abf8dbe1c10d4ff7. Runtime deployment 908598faa17a4192bb42251f7edd499b: ACTIVE_VERIFIED. No new dependencies or database migration.

Added computer Shutdown and Restart, distinct from Stop agent services. The durable existing service controller admits one operation, records progress and dispatch intent, drains Ember through its existing busy/ownership-aware manager, gracefully drains Hub tasks/terminals/downloads and managed models, stops owned MCP/Guard/SSH/Ollama services, closes the owned desktop, and only then requests Windows power. Failed or unverified stops block the Windows request. Windows uses /t 0 without /f; unrelated apps are not force-closed. Uncertain power requests are never automatically replayed.

Added one revisioned startup preference shared by UI, native/offline controls and MCP. The current-user Limited logon task starts the managed agent stack and desktop; optional Ember image models are not started. Automatic recovery respects disabled startup on a new boot, preserves owner-stop markers, and can continue recovery in an explicitly started current session. Startup changes do not stop running services or grant owner permissions.

Controls: Settings > General > Windows startup and computer power; Health & Services offline desktop entry; top health indicator, Tools and tray menus in a newly opened shell. Existing desktop/browser was preserved, so already-running native menus load the update only when the shell is reopened. Ordinary local-chat tools and five MCP tools use the same backend; native tool authorization retains the existing owner gate.

Verified: 23 focused regressions; real Ember preview (four standard services running, two extended stopped); deployed registered MCP handlers against HTTP; startup disable/enable with Windows task readback (final enabled, revision 2); stale revision and unconfirmed power rejected with HTTP 409; actual Windows native and deployed web controls, both restart confirmations cancelled before dispatch. External MellowCodex MCP continued working after deployment. Evidence: E:/AI/artifacts/safe-power-20261111/deployed-settings-readback.json and deployed-ui-readback.json; screenshots alongside. Candidate test receipt: 6289f8b84c464414bc3f4f4b44cfa20e/test-f39f1b4ae8654d23a09ad4626994d3ee.json.

Limits: no physical shutdown, reboot or subsequent Windows logon was performed. Full safe-drain order and failure gates were tested with effect sinks isolated; actual full Ember/agent drain was not performed during this release because live work was preserved. Local generation-model natural-language selection was not exercised (inference remains intentionally disabled); tool visibility, authorization classification, dispatch and UI paths were verified. ChatGPT may need connector tool refresh to see newly advertised tools. A Windows accepted request is recorded as windows_requested, never as physical completion. If Windows is cancelled by an unrelated app, inspect the durable operation and explicitly recover services; no automatic repeat of the power request.

Rollback: first disable the new logon task through the shared startup setting while 0.22.0 is running. Prepare an isolated candidate from the prior release 742efe5179a356516c029d39fdeee41440729b10 and deploy through the existing Guard reviewed workflow, restoring only changed source files from the update backups if needed. Retain state, operation journals and all user data; do not downgrade/delete databases. The older recovery scheduler follows the older startup behavior. Do not treat activate_update(recover=true) as an arbitrary rollback API.

## 0.21.0 — Health & Recovery — deployed 2026-11-11

Task: ef06b2b4072a4ab6ac89fba87e9473ec. Runtime/API/MCP version: 0.21.0 (120 advertised tools). No dependencies added.

### Established causes and changes
The old panel conflated Guard API availability with supervisor coverage, kept one remote-proof record, skipped Repair postconditions, and did not dispatch CLI --status/--preflight. Windows also intermittently omitted an accepting PID: one missing sample followed by two verified PID samples caused a safe but unnecessary Stop rejection. Read-only ownership observations now retry twice; foreign owners still fail immediately.

The shared native/UI/MCP backend now separates process ownership, local API, IPv4/IPv6, routes/DNS, SSH authentication, forwarded HTTP, connector OAuth/external round trip, supervisor coverage and model inference state. Manual Check uses the installed SSH identity with strict known_hosts and a read-only command; no raw SSH logs or tokens are retained. Background checks do not launch SSH authentication probes. Connector evidence has age/last success and expires as stale, not disconnected. Guard OAuth failure affects Guard only. Restart invalidates affected current proof while preserving last success.

Per-service controls and explicit global controls use existing lifecycle mutexes, dependency management, task-impact checks and durable operation IDs. Duplicate active requests share one operation. Repair reconciles only absent supported services and verifies the result; healthy services and intentional stops are preserved. Reset previews stale operation IDs and removes only the disposable health snapshot; it never deletes application data, credentials, permissions, stop markers or action logs. Reconnect directs the owner to the affected ChatGPT connector; it does not complete consent locally.

### Actual verification
- 24 focused health checks passed; after the final read-only ownership correction, the 20 affected checks passed. Existing acceptance tests were not rewritten.
- Four existing independent supervisor activations returned ACTIVE_VERIFIED: 0e2fe9884ba049ea842f92b2276f596e, 523e695155bb49e2972c9369d390b161, 34831643c41d42c68e2de02f9e038b71, febb20281e884291a55b4bedbb46a70b.
- Controlled MCP Stop 274876342147a5b33d4d27aa167af2c8 and Start a95d5cfb077937c7a911a353400268d7 completed. An actual external MCP call failed while stopped and succeeded after restoration; Guard also answered without reauthentication. Scheduled reconciliation respected the intentional stop. Hub, desktop/browser and Ollama PIDs were unchanged during the exercise.
- Actual Windows offline panel remained visible/useful during MCP shutdown: 10 rows, 50 row actions, seven columns, unsupported actions disabled. Final native top-indicator/Tools/tray integration and a real Check-all button produced completed operation 5b0085fc9176f1e6460eecb893b5dc24.
- Registered MCP handlers called the deployed authenticated Hub API successfully; duplicate Check requests shared cd033495a71f6d89d643c2e585925d5f. A direct local MCP attempt using a Hub key was correctly rejected by OAuth and was not bypassed. External MCP transport was verified separately through real connected tools.
- Deployed Check e982519cfa30644257d210889708ed62 verified SSH authentication. Reset fa975f2bf8e04bf4b22fb2be66b84457 completed without changing stale operations. Final Repair f0b2512bf5974d88235aa1626c15e808 left every service unchanged and requested only fresh external proof after its two-minute expiry.
- All 104 existing chats, 10 projects and 1,449 prior task IDs remained present. Protected configuration/credential hashes matched. Inference stayed disabled and the model was not loaded. No skill, permission or user-work deletion was performed.
- Read-only live candidate snapshot: 4.08s. Expanded SSH/DNS/IPv4/IPv6/forwarded-HTTP check: 5.05s (different scopes, not a performance comparison). Public HTTP200 verifies forwarding, not an authenticated MCP round trip.

### OAuth investigation and honest limits
Guard stores opaque-token hashes and grants in its independent private SQLite file outside release directories. Refresh exchange uses BEGIN IMMEDIATE and single-use tokens. Installed defaults are 900s access and 86400s refresh/grant lifetime; the grant expiry does not become permanent on refresh. Existing expired and current grants were observed. Bounded available logs contained no invalid_grant cause. No evidence proves that reboot erased auth, signing material changed, or a refresh race caused this incident. This controlled normal service restart preserved current external Guard authentication.

No computer/router reboot, locked-desktop acceptance, destructive reset or whole-agent Stop-all with active work was performed. The incident's router-versus-server cause remains unknown. ChatGPT consent cannot be automated. ChatGPT may need to refresh its cached tool catalog to expose newly advertised tool schemas. The existing desktop/browser process was deliberately preserved: its already-imported native panel refreshes to new code when that shell is next reopened. The updated standalone desktop shortcut is available immediately.

### Controls, evidence and rollback
Open **Mellow Health and Services** on the desktop, or the native health indicator / Tools > Health and Services / tray menu in a newly opened shell. The standalone command is pythonw -m hub.service_health_ui from the repository and works without MCP or Hub.

Evidence: E:/AI/artifacts/health-recovery-20261111 (transport-e2e.json, offline-ui-readback.json, final-ui-readback.json, final-deployed-verification.json, final-repair-readback.json, candidate-final-network.json, oauth-log-inspection.json). The first safely rejected Stop attempt is retained separately.

For rollback, create a fresh isolated candidate from the installed source and restore the pre-task runtime files from E:/AI/candidates/511a3c49563c49fbb39fe89b60a3264b/source; test and activate through the same prepare/activate supervisor while tasks are idle. Its changed-file backups/journals remain available. Do not overwrite live processes, reset the dirty primary checkout or downgrade/delete the task/OAuth databases. New diagnostic evidence can remain on disk. Packaging version-only metadata is synchronized separately because the existing runtime deployment rejects dependency-manifest changes.


## 0.20.0 deployed verification - 2026-11-10
Before: deployed0.19.0 retained optional long tool/history content under an effective262100-token context. Existing memory and selective tools were already present; this release extends them.
Implemented: shared estimated bounded packets, protected text corrections including older screenshots, current visual evidence, complete tool groups, source-bound compaction, incremental SQLite working state, explicit chat/project pins, and shared UI/MCP settings. No dependencies added.
Deployed through the existing independent SelfDevelop/Guard supervisor:094c145de50b46d9a60b3498e24cc3e7, then final narrow correction437d632625f840a4b7af8f5e378b23c0; both ACTIVE_VERIFIED. Final actual API and MCP version0.20.0,119 tools. Runtime candidate b14b335b2896486d94fe78132afc7c53/r15 plus b1bd937823db4a1da428961a362e8c85/r1.
Validation:34 focused tests; final affected21 tests. Actual deployed normal task bb0d78c5b26a4f848b1bd2627819679a completed one read_file and returned CONTEXT_DEPLOYED_7419. Two calls:10358 input/88 output,14.8977643s model-reported total. Estimates8472/8942 versus actual4888/5470; estimated accounting remains explicit. No extra summarization or embedding inference.
Paired final-packet sample:19621 ->8205 actual input (58.2% less, n=1 pair), wall11.297 ->16.343s. This is not whole-task savings and does not demonstrate latency improvement. No statistically meaningful percentiles or CPU/RAM/VRAM savings established.
UI readback: actual deployed dialog displayed bounded policy and5470 last actual input, no UI error. Source expansion passed. Legacy/shadow/bounded setting transitions persisted through shared validation. Completed task and diagnostics survived final service restart without replay.
Preservation check:103 chats/9 projects before;104/10 after one disposable acceptance chat/project. Task/history counts increased; no data deletion, permission change, model context increase, or model unload was performed.
Controls: conversation memory dialog -> Context & Memory. Final policy bounded, working target12000, configured/effective measured context262100, output512. Rollback setting: context_management=legacy; retained evidence needs no downgrade.
Standalone Guard stage37025ce5c58f49e5bb44d377683b57b4 was not activated: its fixed loopback Hub launcher does not own the installed0.0.0.0 listener. Existing supported supervisor was used; no Guard policy was changed.
Remaining limits: compatible exact tokenizer not established; multimodal token reserve uncertain; full-task30% target and multilingual semantic recall benchmark not established. Semantic retrieval intentionally not installed. Synthetic scope/cancellation/restart regressions are distinguished from the bounded live read workflow.
Evidence: E:/AI/artifacts/context-engineering-validation-20261110 (deployed-live-result.json, paired-actual.json, deployed-ui-readback.json, deployed-context-memory-ui.png, final-runtime-verification.json).

## Context memory 0.20.0 candidate validation (2026-11-10)
Actual isolated ordinary workflow: one read_file, exact expected code, two model calls, 10,286 input / 48 output tokens; no file mutation. Shared HTTP settings set/readback legacy/shadow/bounded passed.
One paired historical final packet, no tools executed: actual input 19,621 -> 8,205 (58.2% reduction); wall 11.297 -> 16.343 seconds. Cache/order and differing output lengths confound latency. This is NOT whole-task savings or proof of faster completion.
Focused tests cover protected corrections, current image, complete exchanges, overflow, incremental recovery, pending identities, cancellation/CAS, source hash/pagination, explicit project sharing and scope exclusion.
No p50/p95 claim, no semantic index, no exact tokenizer claim. Deployment and UI/MCP live evidence must be read from release artifacts; candidate success alone is not deployment proof.
Artifacts: E:/AI/artifacts/context-engineering-validation-20261110.

## Service health panel 0.19.0 - 2026-11-10

Deployment: version 0.19.0 is active in Hub/MCP and the native desktop. The existing independent update supervisor reached ACTIVE_VERIFIED, most recently update 2e92e6cb5bb84010aa0c8651161065e5. Desktop reloads used graceful IPC and retained the existing profile/session. The existing recovery mutex coordinated each deployment; the scheduled task was not disabled.

Actual native UI: top indicator and Tools > Health and Services opened the same panel. Right-click tray exposed the requested service actions; Check was clicked. Service action buttons disabled while a durable action was active. Technical detail is expandable and Guard warning remains visible.

Actual MCP stop/recovery: Stop receipt fcbd79e44437a33423cf4bf27fa0da1b completed. MCP stayed stopped for 70 seconds while the real scheduled recovery task ran (LastTaskResult 0); Hub and Ollama PIDs remained unchanged. After fixes, actual panel Start receipt 9b8965784d42f6e31c4754f96dfb2fe2 and Restart receipt 91188c276f34b0d2cf809c4af4ac5f8e completed on their first postcondition observation. One launcher/interpreter pair per managed Python service and one Ollama process remained; no duplicate copies or active user tasks were present.

Actual offline rescue: with no active tasks, Hub-only Stop receipt 23e5944df7aaf7ebaed8d19f343f373b completed. Port 8876 was closed, and the native panel was closed and reopened visibly without Hub. Start receipt 5519dad90f5ae43c67991b1c5ca04261 restored Hub; Ollama PID stayed unchanged. hub-offline-acceptance.json ended completed with an empty final active-task list.

Actual remote evidence: a nonce delivered to ChatGPT through MCP was acknowledged in a separate MCP call after recovery; verified=true. This proof expires after 120 seconds and is never inferred from an open local port. New named service tools are registered server-side; this existing ChatGPT session did not rediscover them. Shared endpoints were exercised through the existing authenticated MCP exact-command runner, not claimed as new-tool invocation.

Diagnosed during acceptance: controller output pipes could be inherited by long-lived children and prevent completion; file-backed output fixed this. Windows TCP enumeration sometimes lacked an accepting PID for an idle probe; a bounded partial HTTP header materializes the exact reverse loopback tuple, retaining executable/cwd ownership requirements. Explicit actions now wait at most 30 seconds for scheduled recovery's existing mutex. Hub stop recognizes both existing reconciler and supervisor launch forms. Failed/interrupted receipts remain failed/interrupted; no failed result was relabelled successful.

Guard: authenticated status returned healthy=false with started_pids empty. Its supervisor requires the pair it started, so this warning is distinct from reachable Guard MCP. It is not hidden or repaired by changing owner permissions. Model unloaded is shown idle, not an Ollama failure. Network settings were not changed; no claim of fixing DNS or changing IP addresses.

Tests: the 12-test focused health/controller/integration/retry/shutdown set passed (1.64 seconds); the final Hub stop invocation change passed the eight relevant health/shutdown tests (1.37 seconds). These are fixture/code checks, distinct from the native and service experiments above. Ten candidate probes also returned the actual Guard accepting PID. Catalog readback retained 23 installed packages and 100 mapped capability IDs; this is not proof all capabilities work end-to-end.

Local private evidence stays under E:/AI/artifacts/service-health-panel-20261110, including controlled-stop-start.json, final-runtime-acceptance.json (contains successful MCP stages and the earlier Hub-only failure), hub-offline-acceptance.json (the corrected Hub result), and panel screenshots. Runtime data, logs and screenshots are not published in Git.

Limits: no physical reboot, locked-session test, real network outage, OAuth re-consent, elevated broker mutation or destructive whole-agent shutdown was performed. Whole-agent confirmation/task guards were tested as fixtures; actual acceptance used only idle Hub and MCP transitions. User tasks were preserved, not used as destructive shutdown fixtures. This change does not claim to fix previously reported rendering artifacts.

## 2026-11-10 browser interaction repair (0.18.1)

26 focused regressions passed; three Node fixtures skipped. Actual existing Qt page snapshot evaluated successfully and preserved 22/22 controls including the late control previously omitted. Agent-owned interaction after activation: PENDING. No claim of OAuth completion.

## Named browser elements 0.18.0 - 2026-11-10

Candidate 6edcc11400104c198f272642a7b60045 revision 2: tests/test_browser_selections.py and tests/test_conversations.py passed (5 tests, 2.16s). Fixtures covered stable numbers, idempotent save, persistence, Hebrew/English/name resolution, unknown-reference and duplicate-name rejection, rename, and real Conversations.submit context/image assembly without changing the user goal or idempotency. Python compilation and app.js compilation in the actual Qt renderer passed.

Deployment dd1b19b1acb649d3ab55372edf568ce7 reached ACTIVE_VERIFIED. Desktop-only restart loaded the native controls while preserving draft, attachments, conversation and browser state; both views retained GraphicsApi.Software.

Local runner task 506494d561cb4ed6b1152d683d66e970 used the real native toolbar/picker and Save buttons to create two clearly labelled Demo selections from the existing IAB. Native rename was read back through the deployed MCP adapter; MCP rename was reflected when reopening the native list. Hebrew and English instructions referencing both numbers returned both contexts. Multi-selection attached both references to the draft without changing existing attachments. Original draft was restored, and no business task was submitted. Native screenshot 3bd3fe16b50a44f599beafac61e6c8e7 was visually reviewed. The two Demo entries remain only in local state; no snapshots or private data are published.

Final review found a reference-only handoff incorrectly reserving two file slots. Candidate 9d5d060b0382480c8534bde4c8dd7f13 revision 1 corrected the count; registry tests passed (2 tests, 1.45s). Static deployment e86035dc56cb4dfbb74196c0c3834099 reached ACTIVE_VERIFIED. Actual shell reload confirmed the corrected function; a temporary five-attachment fixture accepted reference-only handoff and retained all five, then restored the original draft/attachments/scroll.

Limits: native selection/save/rename/draft and live MCP adapter paths were exercised; an autonomous model carrying out arbitrary requested website edits was not tested. New tools are not yet exposed by this existing ChatGPT session's discovery inventory; external invocation remains pending connector refresh. No claim of physical rendering-artifact resolution, arbitrary-site/iframe support, or persistent live DOM identity. No skill packages, capability mappings, renderer settings or owner security settings changed. Source version 0.18.0 is synchronized; no extra service restart for metadata alone.

## Browser annotation 0.17.0 - 2026-11-10

Candidate7fda11af464c40e7874675b578ee774e revision1: both changed JavaScript modules compiled in the actual Qt renderer. A temporary fixture in the existing IAB verified element click capture without executing its click handler, drag rectangle120x60 and Escape cleanup. Fixture removed afterwards. Existing attachment regression tests:2passed in0.12s.

Deployment402af61f51184d05948399d2acacff5b reached ACTIVE_VERIFIED. Desktop-only graceful restart preserved selected conversation, draft, attachments and IAB scroll; both actual Qt views remained GraphicsApi.Software. No Hub/Ollama task was stopped for the desktop restart.

Native acceptance used the actual UIA toolbar checkbox, CDP mouse events in the existing IAB, the native preview, UIA instruction entry and the native Attach button. Picking a real page link did not navigate. PNG and JSON appeared in the draft; prepare_attachments decoded one image and2083characters including CSS. The deployed MCP adapter listed both artifact IDs. Original draft restored; no agent task was submitted. Native preview screenshot05872dc9916047019e3bf4624e10e5ac was visually reviewed. A second native-toolbar drag produced a200x100region preview; cancelling the preview and Escape in picker mode left no overlay. Registry remained23skills/100capabilities.

One inspection script failed because a UIA automation_id was None; the feature preview was already open. The corrected script continued from that preview and passed; the pick was not repeated. Earlier model-authored implementation attempts stopped without useful code and were replaced with exact commands.

Limits: no arbitrary-site/iframe/closed-shadow-root compatibility claim; no end-to-end model execution was submitted because attachment must remain an explicit user action. The existing attachment preparation path was exercised. MCP adapter discovery passed locally, but new-tool discovery in an existing external ChatGPT session was not tested. This feature does not claim to fix intermittent physical rendering artifacts. Source0.17.0 is synchronized; runtime API version metadata awaits next normal restart.

## Skill Shops presentation 0.16.0 - 2026-11-10

The original title/icon candidate passed four catalog tests. Read-only comparison found eight repaired titles, no damaged categories, 23 packages and 100 capability IDs; versions, capability data and integrity results were unchanged. Search returned three Windows matches and category filtering returned two, then restored all 23 cards in the actual Qt shell.

Color/custom-icon candidate revision2 passed six focused tests in1.83s (test_skill_icons.py and test_skill_shops.py). Fixtures covered static SVG and dangerous-content rejection, raster normalization, persistence, API readback/reset and unknown-skill rejection. Candidate JS compiled in the real Qt renderer. Deployment4faa2824a10542e48f6b6c8b2068450d reached ACTIVE_VERIFIED and updated Hub/MCP without restarting desktop PID9608.

Native-shell validation through the local task runner observed23cards,23icons,18distinct main colors,23file inputs and0question-mark titles. Synthetic File objects were delivered to the real UI file-change handlers for PNG and SVG; both decoded and persisted. SVG survived page reload. The registered MCP adapter read the UI-saved SVG, wrote a PNG with HTTP readback, and observed the UI reset. Test icons were removed and all original defaults restored. Native screenshot d4be2e56b5a744d9be742c9ac7298009 was visually reviewed. Registry remained23installed/100mapped with23valid hashes. No installation/removal or rendering setting changes were made.

Limits: native OS file-picker interaction and refreshed external ChatGPT discovery/invocation of the new MCP tool were not tested; MCP adapter invocation used the actual deployed HTTP service. JPEG/WebP/GIF/ICO were not individually exercised in the shell. No claim of physical artifact resolution; user accepts remaining occasional artifacts for now. Version0.16.0 is synchronized in source; runtime version metadata awaits its next normal restart.

## Modal performance 0.15.5 - 2026-11-10

OpenGL user feedback: faster scrolling, but artifacts returned. Clean prior native screenshots did not establish a cure. Current actual shell reports GraphicsApi.Software in both views.

An initial inline no-blur probe was INVALID because computed blur remained 3px. Corrected CDP inspector stylesheet verified computed none: 189 requestAnimationFrame callbacks in 6049.8ms, mean32.01ms. Restoring computed blur3px reduced this to28 callbacks in6183.1ms, mean220.83ms. This supports blur as a software-mode scroll cost, not as the root cause of presentation corruption.

CSS-only deployment aa66bfc169c74da3af95a8d33c927a28 returned ACTIVE_VERIFIED. After real shell reload, computed Settings and AI backdrops were none;186callbacks in6033.1ms, mean32.44ms,p95 49.9ms. Windows category retained focus after3seconds; native wheel500 remained500 after polling. AI remained modal; resize/minimize/restore completed. Native screenshot was reviewed with no visible corruption; not long-duration physical-display proof. Skill catalog23installed/100mapped. Chat draft, selected chat, shell and IAB scroll preserved around shell restart. No new full180second idle sequence was performed after this CSS deployment; user observation remains required.

No new configurable setting added: software mode is process-only and normal startup returns to the previous automatic mode. Source version0.15.5; API metadata awaits normal restart.

## UI refresh 0.15.4 - 2026-11-10

Deployment b03fa049052e4552b5af6613fc0216b6 returned ACTIVE_VERIFIED; only hub/static/app.js was activated. Real Qt shell reload confirmed newCode=true. Before patch, identical sidebar refresh replaced chat nodes; after patch, chat/project nodes were retained. Search filtered and restored. Collapsed activity summary retained identity; opening populated 9 children. Settings/Skill Shops modal was open and scroll 400 remained 400 after 3 seconds. Native resize to 1180x850, minimize and restore completed. Captured frames showed no corruption but do not rule out presentation artifacts documented by phone. Three-minute OpenGL observation and final interaction checks are recorded separately after completion.

Candidate JavaScript parsed using Runtime.compileScript in the actual Qt renderer. Syntax-preflight regression module: 3 passed; this is tool regression evidence, not proof of UI performance or artifact resolution.

OpenGL actual rendererInterface reports GraphicsApi.OpenGL in both views; no sandbox disable, driver change or persisted rendering setting. This trial is separate from the deployed UI refresh optimization. Source version metadata 0.15.4 is synchronized; no extra restart for metadata.

Final native validation: 180.09 seconds, six scheduled screenshots, all foreground, zero input events, 2693 DOM mutations. All six frames and the AI dialog capture were visually reviewed with no visible corruption. Captures may not reveal physical presentation faults. Summed shell/child CPU averaged 15.42% of one logical core (not whole-machine percentage); this is not a controlled speed ratio against the earlier software trial. Skill Shops Windows category retained focus after three seconds; native wheel scroll 500 remained 500 across polling. AI dialog opened as a modal; Settings opened/closed; returned to selected chat with empty draft. Split view remained usable, and earlier resize/minimize/restore passed. Catalog confirms 23 installed packages and 100 mapped capabilities. User confirmation of physical artifacts and perceived scrolling speed remains pending.

## Skill Shops live completion — 2026-11-10

Guard activation and actual UI install/run/update/remove succeeded. Original 23 packages and100 mapped capabilities preserved. See docs/validation/skill-shops-live-2026-11-10.md for evidence and scope.

## Skill Shops ? 2026-11-10

Candidate revision 22: 15 focused lifecycle, API, guardrail and native authorization contract tests passed. Real installed OwnerBroker returned a verified matching authorization binding under the existing Full policy; no owner policy was changed. Final deployment and live lifecycle acceptance are recorded separately after execution; these candidate results do not imply activation.

2026-11-07 activity home: node --check hub/static/shell.js passed. On the live Hub via Codex IAB, reloaded assets, opened Home, verified 0 active / 3 requiring attention / 0 done among the latest 8, opened task details and expanded actual recorded event history. Screenshot visually checked. The UI correctly did not animate waiting_review as running. Active animation and stale-network transitions remain unverified with a live task. No service restart or model load required for this static UI change.

<!-- MCP correspondence update, 2026-11-07 -->
MCP correspondence development: tests/test_mcp_observation.py and tests/test_conversations.py: 4 passed. Tested registered MCP tool functions against persistent fixture transcript: two reads remain in one chat; cross-project binding rejected. node --check hub/static/app.js passed. These are fixture checks, not production/phone acceptance; active services still require the new code and connector schema.

## Activity indicator development — 2026-11-07

- `node --check hub/static/shell.js` passed after prominent indicator and per-task freshness changes.
- Five focused conversation/progress guard tests passed earlier in this work. These are fixtures, not image integration acceptance.
- Hub HTTP returned 200. IAB inspection encountered a stale connection-error page blocked by browser URL policy; live animation has not been visually verified in this iteration.

# Validation — 5 November 2026

## Independent contract feedback — 2026-11-07

- Same-task resume revision12 took31.77s and read all four requested ranges but emitted a broad implementation plan. Inspection found autonomous `synthesis_request` overriding the narrow director step. Fixed shared read-only fast-mode synthesis to preserve the latest step and requested ranges. Initial new fixture lacked the fast project_context action (1 failure/49 pass); corrected fixture. **50 tests passed16.23s**.
- Repeated same-task correction after the synthesis fix: revision20, **63.17s**, JSON shape now followed but semantics still fail: claims no text-image producer and incorrectly infers no text conditioning from text_encoder=None despite prompt_embeds. Sent those exact contradictions and source statements back to the independent supervisor in the existing conversation. This is not acceptance or autonomous-loop proof.

- Added source-flow `key_read` observations for loaded string-key subscripts, excluding assignments to keys and retaining enclosing conditions. `pytest tests/test_source_contracts.py tests/test_context_modes.py -q`: **49 passed in 16.82s**. Generic fixture checks direct reads versus `.get` arguments and does not infer required user inputs.
- Received a fresh independent ChatGPT contract review in the existing IAB feedback conversation. It identifies unsupported capability generalization, distinguishes defaults/validators/worker inputs, and explicitly says the earlier config excerpt is unavailable. Captured response JSON was checked for expected keys after detecting a stale clipboard capture; the corrected file is `gpt-contract-feedback.json` in the private recovery audit.
- Passed its executor instruction into the actual existing task `26e05b7347934aeaa796a50bd2da653a` through durable guidance and same-task review/resume. Source ranges/tool restrictions were selected by Codex as diagnostic controls. This is a manually relayed external review, not proof of an automatic PLAY/MCP loop. Runner result pending; no project mutation or production deployment.

## Staged extraction transport — 2026-11-07

- The first unschematized recorded-source diagnostic failed: 34.2s, only seven excerpts delivered, top-level array and incorrect field names/enum values, zero accepted components. Preserved private audit `26e05b7347934aeaa796a50bd2da653a-components.json`.
- Added bounded partitioning preserving every source line and original coordinates, explicit oversized-line failure, and opt-in engine output schema. `pytest tests/test_component_analysis.py tests/test_source_contracts.py tests/test_core.py -q`: **48 passed in 28.40s**. Coverage includes real-budget line preservation and mocked transport format forwarding; these are not autonomous semantic acceptance.
- Schema-constrained Qwen3.5:4b diagnostic completed in **139.77s**, five packets covering all 17 recorded ranges. All five returned structured JSON and stopped normally; **14/53** copied quotations matched exact delivered lines, **39** failed. A fixture was also described misleadingly as text-to-video evidence. This is a failed semantic acceptance, not a successful autonomous run. Audit: private `26e05b7347934aeaa796a50bd2da653a-components-schema.json`.
- Follow-up removes source transcription from model duties: the model cites inclusive line ranges, and the host retrieves exact original text. Five component tests passed in 0.27s, including unavailable/reversed/out-of-range rejection. Anchor diagnostic completed **32.05s**, 24 accepted and five rejected under the then-active 4000-character quote limit. The descriptions still conflate text-to-video and image-conditioned video and omit important composition details. Thus semantic acceptance remains failed. The limit was subsequently scoped to model-copied quotes only; host-retrieved text is bounded by the delivered source range. No inference rerun for this limit change.
- Qwen3.5:4b unloaded after diagnostics; Ollama returned no resident models. No GPT, Git, project mutation, production activation, runner integration or new APC reuse.

## Partial-excerpt wiring recovery — 2026-11-07

- Replayed source extraction against the prior autonomous runner's 11 Python ranges: three were unparseable as standalone excerpts. This is a measured input limitation, not proof that it caused every semantic error.
- `pytest tests/test_source_contracts.py tests/test_context_modes.py -q`: **48 passed in 15.82s**. Added complete-unit recovery fixture excluding both cut-off neighboring functions and retaining absolute lines.
- Actual fast-index expansions of `text_image.py:41–98` and `gateway.py:907–1006` now produce complete-unit metadata and 56/60 facts respectively. The former includes the observed `engine_request` call. Audit: private `partial-flow-acceptance.json`. No model inference, project mutation, production activation or end-to-end semantic success was performed in this check.

## Autonomous rerun and measured wiring — 2026-11-07

- After protecting source text from flow-metadata budget pressure, context-mode/source-contract checks: **47 passed in 15.80s**.

- Actual Engine task `26e05b7347934aeaa796a50bd2da653a`, Qwen3.5:4b, English read-only request, no director event/GPT/Git: 143.52s, waiting_review, **not accepted**. It read relevant source but proposed new text-conditioning work despite existing text encoding and missed composing existing image generation with image-to-video. Local critique also made imprecise assertions; it is not an independent oracle. Model was unloaded afterward, verified empty resident list.
- `accept_directed_context.py --autonomous` now explicitly omits director events/guidance and refuses supplied source requirements or a directed-task resume. The probe is not disguised supervised acceptance.
- New static flow extractor: `test_source_contracts`, `test_context_modes`, `test_project_context`: **56 passed in 18.75s**. Tests use unrelated report-render/delivery composition, conditional branches, keyword unpacking, incomplete excerpts, omissions and nonexecution.
- Standalone AST extraction from complete Ember function ranges produced 12/3/29/113 facts for status/create/create/main, including tokenizer and ConditioningItem calls. Private evidence: `measured-flow-probe.json`. This is extractor evidence, not model/runner acceptance of the new approach. Public deployment and full autonomous/feedback gates remain incomplete.

## MCP same-task correction — 2026-11-07

- `pytest tests/test_api.py tests/test_development_api.py tests/test_development_guidance.py tests/test_task_answer.py tests/test_play_protocol.py -q`: **48 passed in 10.96s**.
- Integration fixture calls the registered MCP correction tool through the HTTP review route, verifies queued state on the same task, original objective and tool scope preserved, stale replay rejected, and uncertain actions blocked. The test mocks enqueue; it is not live model execution.
- Current connected tool discovery still exposes submit/get/stop without the new correction tool. Production activation and end-to-end MCP acceptance remain outstanding. `git diff --check` passed with line-ending warnings only.

## Executor answer separation — 2026-11-07

- Broader bridge/core regression check: `pytest tests/test_chatgpt_bridge.py tests/test_core.py -q`: **91 passed in 39.54s**. `git diff --check` passed (line-ending warnings only).

- `test_task_answer`, `test_play_protocol`, `test_development_guidance`, `test_source_feedback`: **30 passed in 2.28s**. Covers stale answers, ambiguous/multiple JSON, duplicate keys, nonfinite constants and unchanged raw text.
- Re-read the isolated real Engine task `4b1ee9908527462d91f94b6231eeaa2c` after its recorded GPT correction: 12 unique cases, 12 correct, required fields correct. The output remains fenced JSON, so strict format compliance is not claimed. Evidence: private `same-task-correction-score.json` in the recovery audit. This is a stored-output check, not another inference or automatic PLAY/MCP acceptance.

## Independent interpretation contract — 2026-11-07

- Updated the shared PLAY/MCP supervisor instructions: independent interpretation before dispatch, original-request preservation, and evidence-based result review. No model was loaded for this change.
- `pytest tests/test_play_protocol.py tests/test_development_guidance.py tests/test_source_feedback.py -q`: **18 passed in 2.26s**. These are software checks, not proof of semantic translation quality or deployment. A new live request-normalization round-trip remains unverified.

## Latest audit checkpoint — 7 November 2026, implementation paused

- Prior pending run completed: `tests/test_core.py tests/test_context_modes.py tests/test_context_integration.py tests/test_model_context.py`: **94 passed in 43.13s**, exit 0. These are software checks, not semantic end-to-end acceptance.
- Reviewed 45 historical acceptance artifacts: 22 cancelled, 3 failed, 17 waiting_review and 3 waiting_user. These runtime states are not correctness grades. Derived inventory remains in the private local audit directory.
- Latest real directed-source trial took 27.31 seconds but missed a requested source and made premature conclusions; not accepted. Git-assisted research is separate evidence and does not establish automatic corrective feedback.
- Read-only hardware/runtime observation: RTX 3050 8192MiB, approximately 31.84GiB system RAM, Ollama 0.40.14; `/api/ps` returned no loaded models. No model was loaded for this audit.
- No new live execution or deployment was performed. The earlier QA restart was rejected by automatic approval review (`blocked by policy`); this audit did not retry it.
- Findings, limitations, primary sources and proposed controlled experiments: [recovery plan](docs/LOCAL_MODEL_RECOVERY_PLAN-2026-11-07.md). Older entries below retain their original scope and dates.

## Executed successfully

| Check | Result |
| --- | --- |
| Python test suite | 26 passed; store, API, interruption, revision control, evidence changes, path boundaries, input guards, native Qt request composition and asynchronous UI delivery |
| JavaScript syntax | `node --check hub/static/app.js` passed |
| Ollama local endpoint | Online; qwen3.5:4b available with tools and vision capabilities |
| Cold text request | `LOCAL_READY`; 69.69 seconds including about 37.72 seconds load time and initial GPU processing |
| Autonomous code task | Completed in approximately 16.37 seconds with an already-loaded model |
| Code-task artifacts | arithmetic.py and test_arithmetic.py created; five unittest tests ran and passed; exit code 0 independently read from the action log |
| Vision fixture | Red shape on left, blue circle on right, text LOCAL VISION 42 recognized, with a missing space in returned text; 13.88 seconds |
| Hub MCP | Initialize, list six tools, call get_capabilities succeeded over stdio |
| Windows-MCP | Initialize and list Snapshot tool succeeded; no UI action was executed by this probe |
| OpenCode | 1.19.5 healthy on authenticated loopback server; session creation through adapter succeeded |
| Native Windows UI | Qt offscreen rendering inspected; Hebrew glyphs corrected by explicitly loading Windows fonts; native submit payload and controls tested |
| Native UI against live service | Loaded the completed task, 6,854 characters of events, and live model readiness with no errors; rendered and inspected in `native-live-preview.png` |
| Global emergency key | Ctrl+Alt+F12 registered according to live capability endpoint; physical key delivery not tested |
| Live restart | Hub restarted after a consistent SQLite backup; completed task remained available |

Evidence is under `E:\AI\artifacts`, including `model-text-probe.json`, `vision-probe.json`, `hub-mcp-probe.json`, `windows-mcp-probe.json`, `native-app-preview.png`, and the code-task review bundle for `6e311b424edc4dfca088a371bf2e2b1d`.

## Explicitly not verified

- Desktop input against a real application/game, DPI/multi-monitor transitions, inaccessible windows, minimized/exclusive-fullscreen game capture.
- The HTTP UI's visual appearance: Codex iab and computer-use runtimes failed before initialization with `failed to prepare MXC sandbox: permission path cannot be represented losslessly`. No external browser was substituted.
- Browser support is now implemented; see the later verification below.
- Ten reboot recovery runs, Windows scheduled startup, or continuation across an actual computer reboot. No reboot was performed.
- Real SSH or service changes on a target server: none was supplied.
- The document's full 50-case evaluation, 90% production target, expert-model comparison, real-time gaming, or parity with Codex.
- Full Microsoft Agent Framework Workflow orchestration. Framework checkpoint storage is integrated; the scheduling loop is custom Python.
- Automatic delegation to OpenCode. The local server adapter was exercised for health and session creation; Hub code execution uses its own tool loop.

## Interpretation

The application is a runnable local pilot with measured code and image behavior. Its presence, installed dependencies, and unit tests do not establish universal control of arbitrary applications or games. The only measured code task here is the small arithmetic example, not a large-repository benchmark.

## Independent browser and locked session update (2026-11-05)

- 36 Python tests passed including durable desktop deferral and automatic queue resumption with simulated session transitions.
- Native unlocked fixture passed real click, Unicode typing, replacement, drag, scroll and stop checks (artifacts/desktop-acceptance/result.json). Arbitrary apps/games remain untested.
- Real local LLM browser task 25c2e25d2c2c436a857c0d1a71b10ae2 completed navigation, field fill, click and verified Saved: LOCAL_AGENT_BROWSER_OK in 16.12 seconds while the runtime was hidden and WTS reported locked/disconnected. Browser uses live DOM fallback when screenshot rendering is unavailable.
- Subsequent task ac45539e61cc42fb940c88a370baa965 performed those actions but incorrectly included the word EXACTLY in the text. Its exact-content acceptance check failed. This is a small-model instruction-following limitation, not a claim of perfect reliability.
- Background UIA fixture: SetValue verified while WTS locked=true/state=4; Invoke returned but no button click event occurred. Do not claim general native app operation while locked. Evidence: artifacts/background-accessibility.json.
- Synthetic Chrome HttpOnly cookie plus localStorage/sessionStorage transfer and extension mock tests passed. Extension has not been installed in personal Chrome and no real account login transfer has been verified.
- Screen unlock/resume tested by state simulation; no real unlock transition or reboot was forced.

- Final locked-session browser acceptance f2aca057261f40259f599b4849e6b0b4 passed exact text verification in 16.14 seconds; WTS locked=true/state=4 recorded before and after. Report: E:/AI/artifacts/agent-browser-f2aca057261f40259f599b4849e6b0b4.json.
- Product run_shell executed and verified BACKGROUND_SHELL_OK 42 with exit code 0 while WTS stayed locked/disconnected. Report: E:/AI/artifacts/locked-shell-check.json.

## Conversation interface update

44 Python tests pass, plus mobile UUID fallback and Chrome bridge JavaScript checks. Real local-model UI testing confirms two-turn recall and transcript persistence after reload. Responsive layout measured at 1440px and 390px with no horizontal overflow; offscreen Qt desktop/mobile renders inspected. File preview traversal, project notes, worktree isolation, attachment validation, schedule dispatch and emergency schedule pause have dedicated tests. Feature boundaries and official research links are in docs/UI_CAPABILITIES.md.

## Native login and bidirectional visual feedback — 6 November 2026

- 93 Python regression tests passed in 17.34 seconds. JavaScript syntax, mobile UUID fallback and extension transfer fixture tests passed. Regressions cover virtualized chat anchors, old-turn rejection, multi-stage login detection, physical input preference, duplicate image exclusion, current-attempt evidence and screenshot request repetition.
- Real Walla task `6b092360d5bb49d5bb546a03b3401648`: local semantic navigation closed an owned Edge translation popup, followed the observed `mail` hyperlink, and reached `https://friends.walla.co.il/#/login`. It used the existing tab. The visible form contains an email field and Continue button; no credentials were entered. Navigation took 7.75 seconds, excluding later local inference and final ChatGPT review. The final screenshot was visually inspected here and ChatGPT returned an explicit positive visual review. Evidence: `E:/AI/artifacts/login-navigation-acceptance.json`.
- The first screenshot test exposed an obsolete listener anchor after ChatGPT virtualized its history. Fixed recovery uses stable turn order when the stored anchor is absent; regression tests also reject older turns. A second attempt exposed repeated screenshot requests caused by re-inserting the original wording after every image. The observation message now identifies a completed action without reissuing that request.
- Clean final screenshot test `77565a08f4424c7d93043915b7db03b2`: a plain-language ChatGPT request triggered exactly one `capture_screenshot`, produced a valid original 1792×1120 PNG, delivered exactly one attachment, and received “Final screenshot captured and received.” The measured task-to-delivery interval was 9.89 seconds; request-to-delivery was 18.56 seconds, including the initial ChatGPT response. These are individual measurements, not a service-level guarantee. Evidence and hash: `E:/AI/artifacts/desktop-share-acceptance.json`.
- Model and visual assistance controls were exercised in the product's own embedded UI. Continuous mode survived reload, then smart mode was restored; no JavaScript page errors were observed. The settings screenshot was visually inspected: `E:/AI/artifacts/model-visual-settings-verified.png`. Live progress was observed in the actual desktop screenshot and the progress API returned HTTP 200 during execution.
- The app remains running with the saved ChatGPT conversation and continuous listener enabled. Fast local inference preset and smart visual assistance remain selected.

Limits: the continuous visual mode's settings persistence was tested, but a full multi-step live workflow in that mode was not run. The final live navigation used accessibility controls; physical preference has regression coverage and earlier fixture evidence, not a new general application acceptance test. Cross-device arrival was simulated by a newly submitted message in the linked web conversation, not by operating the user's phone. Existing external browser tabs were preserved. Arbitrary games/apps, native control while locked, and full Codex parity remain unverified.

## Documentation and version consolidation — 0.3.0, 6 November 2026

README now consolidates the implemented features, fixes, usage, evidence and limitations. CHANGELOG records the delivered changes; AGENTS requires release notes for future fixes, updates and upgrades. Package/source/API version consistency was checked at 0.3.0; the API imports the shared source version instead of its former 0.1.0 literal. Documentation relative links, listed source paths, UTF-8 and fenced code blocks passed checks. All 11 API tests passed in 3.45 seconds after the metadata change. The running service was not restarted for this documentation update; it loads the new version metadata on its next normal restart.

## Listener recovery and usable screenshot attachments — 0.3.1, 6 November 2026

- 101 Python tests passed in 19.07 seconds; `node --check hub/static/app.js` passed. Regression coverage includes renumbered turns after reload, an archived but unexecuted request, missing stable anchors, duplicate prevention, draft/generation/overlay guards for idle refresh, image load verification and bounded correction after a failed file-share tool call.
- The earlier turn-order recovery claim above is superseded: ChatGPT fallback turn numbers can reset on reload. Live state retained order 27 while current turns were numbered 0–5. Authorization now requires a stable message-ID anchor, with the last authorized human message as fallback when the agent feedback is absent. When neither anchor is present, execution is deferred visibly rather than granting authority based on DOM numbers.
- Idle cross-device refresh is guarded at 30 seconds without activity. Fixture tests simulate a remote arrival and draft changes immediately before refresh. Real refresh was observed in the linked conversation; the user's phone was not operated in this test.
- Live task `c139c2cbb409454ab1d3748823c0347b` executed exactly one `capture_screenshot`, registered a valid original PNG of 1792×1120 pixels (205,619 bytes), and delivered one attachment with `attachment=verified_image`. Task-to-delivery was approximately 12.48 seconds; test request-to-delivery was approximately 24.82 seconds, including the initial ChatGPT response. These measurements are not latency guarantees.
- The actual original attachment was opened in the product's embedded ChatGPT viewer: the image loaded with natural dimensions 1792×1120 and no file-load error. Its screenshot was visually inspected. Evidence: `E:/AI/artifacts/listener-recovery-acceptance.json` and `E:/AI/artifacts/listener-original-attachment-open.png`.
- A subsequent human request for a fresh desktop screenshot produced task `3cefca36164848f388d4049c710b7911`: one capture, a 204,193-byte PNG, and verified image delivery. The device used to submit that request is unknown. A further human request was then detected and dispatched without manually resetting the listener.
- The prior reported PNG itself was valid and its original attachment loaded. The additional download link generated in ChatGPT's answer failed. The bridge now directs ChatGPT to the real original attachment and checks actual image loading before reporting delivery. ChatGPT still generated an additional link during the new test, so link-generation compliance is not guaranteed; opening/downloading that extra link on the phone was not validated.
- Version 0.3.1 is loaded by the restarted hub service. The existing embedded browser process, profile and login were preserved.
# אימות 0.4.0 — 2026-11-06

- 136 בדיקות pytest עברו ב־23.05 שניות. כולל עומס בתור ללא אובדן בקשה, התחלת עבודה לפני אישור מרוחק, סינון חלון Explorer, התאוששות לשונית, הקשר מודל, פקדים מוסתרים/מכוסים, צירופים, הרחבות ומסמכים. רוב הבדיקות סינתטיות; בדיקות DOM מריצות את JavaScript האמיתי על fixtures.
- בדיקות מתאם ישירות: לשונית Qt שקרסה חזרה באותו מזהה לאחר reload. הדפסה מקורית של אתר החזירה גם PDF עם פרסומות החוסמות את התוכן; לכן אינה נחשבת הצלחה חזותית.
- PDF קריא של כתבה, שהופק ישירות במהלך פיתוח, רונדר ונבדק חזותית בשני עמודים. זהו תוצר בדיקה בלבד, ללא תמונות, ולא ביצוע של משימת המשתמש בידי הסוכן. הועבר מחוץ לתיקיית העבודה; טיוטת מסירתו בוטלה ללא שליחה.
- קובצי Word/Excel נבדקו ב־round trip סינתטי; לא נבדקו חזותית ביישומי Office. PDF עברי מעורב נבדק בנפרד. לא בוצעו בדיקת נייד, אתחול Windows או מסך נעול לעדכון זה.
- ריצת הסוכן עצמו `99117bc7aaa8454faf02c724aec838d6` בחרה את הכתבה `https://www.walla.co.il/news/breaking-news/383960340` באמצעות קישור שנצפה, הפעילה `browser_save_pdf(layout=page)`, `file_copy`, `document_read` ו־`file_share`. הפלט `E:/AI/repos/sandbox/walla-article.pdf` הוא PDF בן 3 עמודים, 4,283,988 בתים, SHA256 `a0dad32cf570a9cddad69484fde8062745ff7a949157a2a4b2aee49993e8ca1a`.
- שלושת העמודים רונדרו ונבדקו חזותית בידי המפתח (לא בידי הסוכן): הכותרת בעברית וטקסט הכתבה קריאים; קיימים גם תמונה, פרסומות ושאריות ממשק האתר. אין טענה ליצוא נקי או לעריכה מושלמת. ראיות: `E:/AI/artifacts/agent-pdf-acceptance/page-1.png`, `page-2.png`, `page-3.png`.
- ניסיון המסירה הראשון נכשל לפני שליחת ההודעה, כאשר לשונית ChatGPT ברקע הייתה בגודל אפס ושדה ההודעה לא היה נגיש. לאחר אבחון, הוסר רק צירוף הטיוטה של הניסיון הכושל, נרשמה התאמה של מצב המסירה, ומתאם Qt תוקן כללית. השירות והדפדפן הופעלו מחדש תוך שמירת הפרופיל. לא נוצר PDF חלופי ידנית ולא הורצה שוב משימת התוכן; הגשר של הסוכן חידש את מסירת הפלט הקיים.
- הודעת הסוכן `1fb80a6b-9dfb-420c-97c6-b9f2ddab6ff6` כוללת כרטיס ממשי בשם `walla-article(2).pdf`; validator הקבצים החדש עבר על ההודעה הקיימת. ChatGPT השיב שקיבל ובדק את שלושת העמודים. לא הורד הקובץ חזרה להשוואת hash, ולא נבדקה הורדה מהנייד או תקינות קישור נוסף ש־ChatGPT יצר. ראיות ממוקדות: `E:/AI/artifacts/agent-pdf-acceptance/delivery.json`.
- תיקוני התכנון, הכלים והמסירה משותפים למודלים; הקבלה האמיתית הזו בוצעה עם המודל המקומי הנבחר בלבד. אין הבטחת הצלחה בכל אתר או מודל. התאוששות מלאה ללא התערבות מפתח לאורך כל הריצה לא הוכחה, משום שהתיקונים הוחלו בין ניסיונות.
- בבדיקת מצב ההאזנה לאחר המסירה נמצא תור ישן עם הודעת `#` שתשובתה כבר טופלה. נוספה התאמה כללית המוציאה בקשה כזו מהתור ללא הרצה חוזרת; fixture כולל הוראת פעולה שכבר טופלה ומוודא שלא מתקבלת משימה נוספת.



## 0.5.0 — public MCP bridge, 6 November 2026

- Full Python suite: **141 passed in 25.78s**. `node --check hub/static/app.js` and `node tests/test_extension.cjs` passed.
- Five new regression tests cover PKCE rejection, authorization-code replay, refresh rotation, revoked access, authenticated tool discovery, redirect restrictions, signed file delivery/tampering/expiry, stable submission dispatch and strict loopback SSH forwarding. These are fixture/adapter checks, not autonomous desktop acceptance.
- Remote deployment: independent SSH user/key, loopback 18897, HTTPS virtual host `agent.178-128-45-70.sslip.io`; nginx and sshd configuration checks passed. SHA256 values of existing Ember Table/Video nginx files, SSH match file and authorized_keys were unchanged. Ember apps were not running their tunnels at inspection time; their business functions were not retested.
- Public health and both OAuth discovery documents returned HTTP 200. Unauthenticated MCP returned 401. Live OAuth used client_secret_post plus PKCE and explicit approval through the authenticated local API. Test grants were revoked after each run (HTTP 200; subsequent access HTTP 401). No user account connector was configured by this test.
- Agent-owned live acceptance via public MCP: task **213894ee63af4bd995bd1191b060b637**, saved chat **19d2852658a745b5bdedee9dc1a6347c**. Submission returned in **0.344s**; completion observed at **5.33s**. The local model called `list_files`, recorded its actual result, and entered `waiting_review`. Duplicate submission returned the same task and exactly one saved turn. No developer performed the task's file inspection on the agent's behalf.
- An earlier acceptance task also executed successfully, but the developer assertion incorrectly expected `completed` instead of the store's `complete` action state. The assertion was corrected and the acceptance rerun; this was a test error, not an agent task failure.
- Separate developer file fixture: UTF-8 Hebrew text uploaded to the local library, retrieved through MCP `get_file` and downloaded through public HTTPS. Bytes matched exactly; SHA256 **359003622272ced0fff61331bbf9c560ebc0285336d97b22f1de2878c009b3fd**. This does not test ChatGPT attachment rendering or phone downloads.
- Evidence: `E:/AI/artifacts/mcp-acceptance.json`, `E:/AI/artifacts/relay-reconnect.json`, `E:/AI/artifacts/remote-settings-review.png`, `E:/AI/state/mcp/deployment.json`. Evidence contains no OAuth tokens or root password.
- Forced termination of this integration's SSH process only: supervisor created a new SSH process and public health recovered in **6.75s**. This tests tunnel recovery, not Windows reboot or every process-crash scenario.
- Qt offscreen settings screenshot was visually inspected: Hebrew text readable, connected status and public MCP address visible. The full-size model-settings dialog remains scrollable.
- Hub port migrated to **8876**; running API reports **0.5.0**. Existing local chats, task history and browser profile retained. Tailscale phone access on the new port was not tested.
- No claim of full Codex parity, guaranteed latency, Windows locked-screen mouse control, or resolution of every existing browser-listener issue. This release adds an independent authenticated dispatch path.


## 0.5.1 — 2026-11-06
- Full suite: 144 passed in 24.79s. New regression cases cover listener timeout releasing the runner lock, short MCP completion, and an active task at the wait deadline (never reported as success).
- Original user screenshot task 8ada50f1cfd0412eb9dba90d74d06ada recovered from queued and executed capture_screenshot through Engine; PNG registered as 1562ff0dc5754e50808e87393ea97834. Delivery into the user's ChatGPT conversation has not been observed.
- Public OAuth/MCP agent-owned inspect acceptance: fcf8aa3acb7140bcbb1a149047e54b88 returned within 4.156 seconds; repeated request ID did not duplicate execution.
- Public screenshot acceptance: first capture returned within 6.813 seconds; its developer download assertion failed because compact tool evidence was a JSON string, not a dict. Corrected the acceptance parser. A second complete run 015e2244179541139b6f103d611e8723 took 20.62 seconds through result polling and verified original image download SHA256 b9ebe003a2f4e2135bc866994677a6ab6443a8b3b4711c6aa2a14c93c94d8af9. Temporary test OAuth grants revoked; user grant retained.
- Public health verified 200, version 0.5.1. Actual desktop process reports visible main-window title Local Agent — התכתבות לצד ChatGPT. Duplicate launch during startup was rejected rather than opening a competing profile; a subsequent show request succeeded. Tray icon placement within Windows overflow was not visually verified.
- Limitations: ChatGPT client must continue polling long work and call get_file for returned images. Actual user ChatGPT message rendering, phone display, reboot and locked-desktop operation not verified here. Idle observation can still delay dispatch up to its 15-second bound; timings above are measurements, not latency guarantees.
`nFinal targeted checks after preserving status publication during active jobs: 13 passed in 3.42s. Backend reloaded; public health rechecked.

## 0.5.2 — 2026-11-06
Full regression suite: 147 passed in 24.63s. New fixtures validate Hebrew/English close-request detection, rejection of observation-only completion, browser-mode tool availability, all-or-none target validation, and use of native RequestClose. Public health verified 200/version 0.5.2 after reload. Saved browser session preserved on graceful desktop restart.
Live tab closure through the user's specified ChatGPT conversation is NOT verified: Codex iab automation failed before accessing the page with MXC sandbox path error. No alternate live closure was substituted. User must send the test from that conversation; the agent records resulting actions for subsequent verification.

## 0.6.0 — 2026-11-06
149 tests passed in 26.11s. Includes mocked MCP stage notifications and notification failure isolation. Actual ChatGPT conversation could not be inspected: Codex iab automation failed initialization (MXC permission path cannot be represented losslessly), including retry after reset. ChatGPT notification rendering and visual UI acceptance remain unverified.

## 0.7.0 — 2026-11-06
151 regression tests passed in 25.68s. Agent-owned task fc8bae9a84314d9390a06febbefe4659 used agent_environment, desktop_shortcut inspect and create; recorded verified target E:\AI\Start-Local-Agent.cmd at C:\Users\MellowYak\Desktop\MellowCodex.lnk. This is actual runner acceptance, not direct adapter execution.

Launcher acceptance: normal IPC shutdown confirmed no agent window; launching the agent-created .lnk then produced a visible Local Agent window. Services remained reachable (UI HTTP 200). Launch test is direct operational verification; shortcut creation was performed by the agent runner.

## 0.8.0 - 2026-11-06
154 tests passed in 26.54s, including real native shell exit-code/output checks. Agent-owned task 6d18707632ef4271a22ddb8d6c2ca755 selected powershell and cmd, returned PS_OK and CMD_OK with exit code 0 for both. No administrator/elevation or arbitrary-command coverage claimed.

## 0.9.0 - 2026-11-06
Initial suite: 153 passed, 2 native API mocks failed after changed DLL binding; corrected mocks and reran affected application/terminal tests (7 passed) and recovery tests (5 passed). Agent-owned terminal task 167899fcaffb4b8699e540b76fa2503e observed START while running then FINISH with exit 0. Agent-owned close task 8c4310fa89f243c6a813588ed2fd54df confirmed Win32 error 5 and Task Manager remained open. No successful closure claimed. Interactive SSH/PTTY and ChatGPT client rendering unverified; not complete capabilities.

## 0.9.1 - 2026-11-06
156 tests passed in 27.94s. Agent task 54be29f60ed94c4dbce4ccdeea2703c1 used agent_environment then app_close without shell retries. Executor elevated=false; close returned Windows error 5 and remaining Task Manager window. Closure NOT completed. The restarted executor is not elevated; prior UI elevation is not proof of backend elevation.

## 0.10.0 — 2026-11-06: model memory and quick selection
- Full regression suite: 160 passed in 27.43s (installed Windows Python, elevated tool execution).
- Four mocked Ollama tests cover verified switch with saved selection, failed load retaining selection, rejection of missing models before mutation, and unload-all/reload.
- JavaScript syntax: node --check hub/static/app.js passed.
- Actual sidebar interaction, live model switching and remote ChatGPT MCP invocation are NOT yet verified. The elevated service restart was canceled at Windows UAC; running services have not loaded these changes. Requires an approved administrator restart and UI refresh.
- A failed switch can leave the old model unloaded while retaining its selection; subsequent inference reloads it. A separately configured coding model is unchanged.

## 0.10.1 — 2026-11-06
162 tests passed in 33.55s. Fixture-driven Engine task completed 35 tool steps and reached waiting_review, demonstrating removal of the 30-step cap. Silent-shell guard tests cover duplicate rejection and allowance for changed arguments/results or intervening observation. Reported VS Code task e03de96fd99a400da95dc3e465347369 was read via local diagnostics: repeated identical empty shell results, then waiting_user at 30 steps; no successful launch verified. New live agent acceptance remains pending administrator-approved service restart; no manual VS Code modification performed.

## 0.10.2 — 2026-11-06
163 tests passed in 34.11s; JavaScript syntax passed after timeline expansion-state preservation. Fixture validates active command ID, step, wait reason, expected output, unknown total and blocked-state polling. Updated old get_task polling assertion for new wait_task contract. Live checks after user reopened UI still returned 0.9.2 from backend and gateway. UAC restart returned cancellation again. Version-aware administrator startup and live MCP/UI timeline remain unverified in the running services; not claimed deployed.


0.10.3: Python compilation and PowerShell parser validation performed. Live UAC activation and restart have not yet been verified.


0.10.4 (2026-11-06): Manual unload pauses active agent jobs and persists disabled local inference until explicit load/switch. Main and coding inference respect this flag. External Ollama clients are not controlled. Live restart/VRAM acceptance pending.


0.10.5 (2026-11-06): Preserve process name when executable-path access fails. Application inventory exposes unresolved title matches and refuses verified absence/closure when identity is unresolved or close delivery failed. Generic fixture added; live application closure not yet verified.


0.11.0 (2026-11-06): Configurable screenshot transport JPEG quality (30–95) and longest edge (640–3840), default 1600/75. Settings UI and MCP screenshot_settings tool; applies to local inference images, requested screenshot exports and ChatGPT visual evidence. Originals retained for native-coordinate input. File size is content dependent; no fixed KB guarantee. Live delivery/restart acceptance pending.


Vision benchmark — 2026-11-06: Actual local Qwen screenshot feedback, one desktop capture, warmed model, two runs per variant in reverse order. Prompt differed only in trial number to reduce prefix reuse. Original 1792x1120 PNG 1,206,987 bytes: 3.010/2.947 seconds. JPEG quality35 same dimensions 143,000 bytes: 2.836/2.856 seconds. JPEG quality35 960x600 49,413 bytes: 1.538/1.463 seconds. Prompt tokens 2022/2022/632 respectively. Simple app/text-label identification only; no OCR or coordinate accuracy acceptance. Original/JPEG responses incorrectly guessed Edge/Chrome for embedded Local Agent browser. Small version recognized Local Agent but fine text visibly degrades. Raw results: E:/AI/artifacts/vision-benchmark/results.json. This does not benchmark MCP latency or prove general accuracy/speed. Settings were not changed; model unloaded afterward if initially absent.


2026-11-06 Hebrew OCR trial: qwen3.5:4b, supplied contract photo, identical transcription prompt, JPEG quality85 at 720x960,1200x1600,2880x3840. Wall times 30.89s,23.33s,25.63s; first included4.52s model load. All three outputs visibly garbled; none accepted as reliable transcription. Single run per resolution, different output token counts; not a controlled throughput comparison. Raw outputs E:/AI/artifacts/qwen-hebrew-ocr/results.json. No persistent model/image settings changed.

### 2026-11-06 Hebrew OCR diagnostics (0.12.0)
- Qwen + Tesseract draft: 21.78s, failed exact transcription.
- Hebrew specialist CPU: 7.15s original; 7.12s geometrically rectified; 7.46s larger detector input. Larger detector did not consistently improve quality.
- Final adapter: 7.07s including model initialization/recognition/layout processing (subprocess overhead excluded). Output readable, with remaining character and ordering errors; no numerical accuracy score or perfect-transcription claim. Original photo remained unchanged.
- `pytest tests/test_image_ocr.py -q`: 2 passed (0.23s), missing-engine and workspace-boundary checks.
- Full ToolRunner attempt canceled after initialization stalled before producing artifacts. Direct adapter succeeded; this is NOT agent end-to-end acceptance.
- Results: E:/AI/artifacts/qwen-hebrew-ocr/readable.html, readable.txt; machine evidence: E:/AI/artifacts/hebrew-ocr-acceptance/.


### 0.13.0 visual assistance
- Four isolated tests passed: destination-specific dimensions and unchanged originals, OCR opt-in/cache/evidence labeling, existing OCR adapter tests (0.80 seconds).
- compileall hub passed. Broader visual recovery tests stalled in desktop-dependent ToolRunner construction and were interrupted; not counted as passing.
- Live process restart, visual UI inspection, OCR/ChatGPT correction roundtrip, and MCP callback behavior have not been validated. No end-to-end success claim.

### Live agent acceptance — 2026-11-06, document/UI follow-up
- Submitted the actual user-provided Hebrew photograph as `visual-document-test.jpg` in the sandbox workspace through MCP, task `d617de58d32249ee97ec46163b91c33b`.
- FAILED: running agent tried document_read (PDF/DOCX/XLSX only), searched for OCR, then repeated a PowerShell 5-incompatible `||` command. State waiting_user after six actions. No transcription or visual comparison completed; image_ocr was not invoked.
- Requested service version alignment through the existing launcher; Windows UAC approval pending. No updated-runtime success claimed.
- Independent computer-use initialization failed with `failed to prepare MXC sandbox: permission path cannot be represented losslessly`. Random-window visual acceptance has not yet run.


## OCR-on / ChatGPT-off actual task-runner acceptance — 2026-11-06

- Successful image_ocr calls now attach the original image through the configured local image transport to the next model turn. OCR remains supplementary, untrusted evidence. This applies to all supported local models and workspace images.
- Added scripts/ocr_agent_acceptance.py for real local task-runner document acceptance, retaining actions/results in an isolated persistent store.
- Actual Qwen 3.5 4B test with OCR on and ChatGPT feedback off: 23.39 seconds after image delivery fix (20.58 seconds before). Recognized a rental agreement but retained character and reading-order errors in clauses 16–17; full transcription accuracy did NOT pass.
- Running service observed at 0.10.5; this acceptance used the updated on-disk engine, not that older service.

Task: 67e7ec46b3ae493d9a138d4ec6099fb0. Action log contains image_ocr only; no ChatGPT calls. Report: E:/AI/artifacts/ocr-agent-acceptance.json. Source comparison found במחסך instead of במחסן and misplaced words in the final sentence of clause 16. Model output also ended mid-sentence. No desktop UI or live MCP acceptance is claimed.

## 0.13.3 desktop-independent OCR regression
Three tests passed in 0.33s with normal local execution. OCR worker is mocked; the desktop stub rejects every desktop query except the global stop flag. Python compilation passed. Sandbox test run stalled after two tests; this is not locked-Windows acceptance. Background replanning and live service activation have not been verified end-to-end.

## 0.13.4 background recovery — 2026-11-07
Controlled real-runner test 69ce53f4afb84056b0bc56c850292f9d: initial model/tool desktop call injected as unavailable, then real Qwen and real OCR. Actions observe_screen (deferred), image_ocr; waiting_review after 23.39 seconds. No ChatGPT call. Recovery passed; Hebrew transcription retains errors. Not a real Windows-lock acceptance. Initial core run: 22 passed, two fixture failures (user feedback setting and invalid image bytes); fixtures isolated/corrected without changing live settings.

Final targeted regressions: 25 passed in 12.92 seconds (core task runner and OCR adapter). Launcher activation requested; Windows UAC pending at time of recording.

## Requested repeat OCR acceptance — 2026-11-07
Actual updated engine, no injected calls/failures, task b773723229ce44d5a22dfade4936eb43. OCR on; ChatGPT feedback off. image_ocr succeeded, then model attempted read_file on the JPEG (too large), then on generated OCR txt/json outside workspace (correctly denied). waiting_user after 26.36 seconds. End-to-end acceptance FAILED despite successful OCR. Live hub and gateway still 0.10.5; prior launcher remains waiting. Report E:/AI/artifacts/ocr-agent-acceptance.json. No real locked-session acceptance claimed.

## 2026-11-07 — ongoing OCR acceptance

- 31 targeted unit tests passed before the latest two-recognizer worker change (not desktop acceptance).
- Real Qwen task f36e844d14a64e84b55d47beeee75382: 44.2 seconds, three image_ocr calls, readable ordering but a remaining final-letter error.
- Real Qwen task 1551e1f5c15d491fb2d328ec92f3dbe3: 180-second timeout after 19 OCR calls with repeated crops; not successful. ChatGPT feedback disabled.
- Real session diagnostic reported locked=true, interactive=false. Existing image reading does not verify live window capture or input under lock.

## 2026-11-07 background capture development
- 14 focused fixture tests passed: desktop guards/background selection/GDI fallback, source-region offsets and bounds, model context.
- Actual agent test e30043d0d94b4a5290a16e2d4c9743c4 reached list_windows/window_inspect but failed at context-budget handling in 12.89s; not a successful visual acceptance.
- Post-reboot MCP task 03c281ed868b425081e279c46c755ca2 returned a real two-monitor desktop screenshot (86,635 bytes JPEG); Windows was unlocked. This does not establish locked-session support.
- Earlier document agent tests 50e30d9c32c1467b925365c787ca76b9 and 5002b9b609af435ea8fd3f89caebbbe0 returned readable clauses 16–17 with punctuation omissions, in 36.06s/34.84s respectively, without ChatGPT feedback.
- Changes remain Unreleased pending live acceptance and deployment; fixture success is not locked-desktop acceptance.
`n- Actual agent b2dcb851e91043abaf12651be391c4ef captured the non-foreground Local Agent window with target-window-printwindow, no physical input, in 21.58s. Returned image visually inspected: actual application content, 83,976-byte JPEG. Windows remained unlocked; this validates background-window rendering, not locked-session acceptance. The broader desktop/visual/OCR test run stalled and was interrupted; no pass claimed for that run.

## 2026-11-07 tabbed application diagnosis
- Historical task 2933ce45938f4f41ae947bd936099a2a contained dozens of repeated coordinate clicks. Delivery of input was mistaken for progress.
- Live read-only task dc379e2e62c8496fbc0a41a139bf2b7d (15.28s) exposed a context-loss bug: UIA recorded 16 tabs and the last selected jokes-notepad.txt, but model reported two inactive tabs. Selected-tab prioritization and explicit summary added.
- 17 targeted fixture tests passed, including selected-last-tab retention, repeated-input blocking, capture regions, and desktop guards.
- First live writing acceptance 8f5867378a28445abc63db1de172d987 failed in 63.92s: invalid coordinates and unsupported UIA click spelling. Not claimed successful. UIA click alias added before retry.
- Shared typing regression tests validate Hebrew, newline key events and intact emoji surrogate pairs. 18 focused tests passed. Further live retries remained unsuccessful; deployment is not yet claimed.

- 0.14.0: live local-agent task 09adc2beab4c447194821c52472bdfa5 succeeded in 16.89s using window_new_document and capture_screenshot. Three Hebrew jokes and line breaks matched UIA readback; final image visually checked, no blocking error dialog. Existing tabs preserved; test-created tabs remain open. 20 focused tests passed in elevated Windows environment; sandbox test run stalled. Other editors and locked-session interactive input remain unverified.

## 2026-11-07 — APC context foundation (development)

18 tests passed: test_project_context, test_model_memory, test_model_context, test_extensions_documents. Synthetic fixtures verify source freshness, annotation persistence, multilingual retrieval, scope exclusions, AST relationships, idempotent APC metadata import and recovery. UI/runtime additions followed this run and require new validation. Live model/UI/MCP acceptance remains pending.

Practical context acceptance and failed-attempt analysis are recorded in docs/DEVELOPMENT_IMPLEMENTATION_STATUS.md. Real model run used search/expand/related and passed the unchanged synthetic test. IAB UI search and annotations verified on isolated service. Public connector acceptance still pending.
# Plan reconciliation audit — 2026-11-07 (development source)

- Read original Codex chat `01a11fa8-42ea-71c1-9f92-7ade0ca7c9f9` (בנה את מערכת Ember Table), technical plan/mirror, handoff and source. No Ember product changes.
- Rechecked 24 pinned APC hashes and 142 source ZIP entries: all match. Persistent backup hashes match; both SQLite backup integrity checks return ok. Manifest-listed hub.sqlite3-wal/shm are absent; full application restore drill remains unverified.
- In isolated LOCAL_AGENT_ROOT, ran `python -m pytest tests/test_project_context.py tests/test_context_integration.py tests/test_core.py tests/test_model_context.py -q -p no:cacheprovider`: initially **35 passed, 1 failed in 16.89s** (missing context.register_tool). After completing all three locale descriptions in en/he/ru: **36 passed in 16.49s**. Fresh isolated `import hub.mcp_gateway` succeeds.
- Disposable fixtures reproduced four open gaps: disabled setting still schedules a scan; a request during an active scan loses its immediate follow-up; preserved-size/mtime edits leave search stale; long optional notes can omit required constraints from overview. Evidence and harness: `E:/AI/audits/plan-reconciliation-20261107/findings.json` and `probes.py`.
- Reread historical real Engine actions in context-acceptance-20261107-c: successful source retrieval/edit and pytest exit 0, with two recovered tool errors and final waiting_review. This is reused historical evidence, not a new acceptance run.
- No model inference, UI/browser session, fresh public ChatGPT acceptance, service restart, deployment or version release in this audit. Current exposed connector inventory has seven legacy task/chat/file tools and no context/index tools. Source registration and public discovery remain distinct.


## Index queue lifecycle — 2026-11-07

11 tests passed in 3.58s: test_context_indexing, test_project_context, test_context_integration. New cases exercise settings without scanning, explicit refresh while disabled, a concurrent request during a scan, and retry after failure. Fixture evidence only; cancellation/shutdown live acceptance and UI/MCP/agent activation remain pending.

### Active implementation: context and local indexing tools — 2026-11-07

- Required constraints are separated from optional annotation notes and pinned in the fixed model packet; oversized required data raises an explicit limit.
- Refresh now detects same-size/same-mtime changes using content hashes and extractor identity, and refuses missing roots before deletion reconciliation. This correctness-first implementation rereads contents on refresh; incremental performance optimization remains open.
- Local task tools now expose current-project index requests/status/background settings through the existing shared queue. The UI shows readable source/search/relations, optional technical JSON and background status/settings. Practical UI acceptance remains pending.
- 42 focused tests passed in 18.99s before the final fixed-packet/UI addition; 15 context/integration/indexing tests passed in 13.39s afterward. JS syntax check passed.
- Real isolated Engine run de0d65b8ed6746e6957d4cf123d95610 used context_search/expand/related, edited billing.py, preserved its test and ran pytest successfully in 34.38s. Final state waiting_review. Evidence: E:/AI/audits/context-live-20261107-resumed/acceptance.json. Ollama reported no loaded models afterward. This validates a narrow real-agent repair, not all plan phases.
- No production restart or release. Phase 1 and all subsequent completion gates remain active work.

### Continuing Phase 2 foundation — 2026-11-07

APC design contracts from project_connection.php (source/work location separation) and project_source_history.php (content identity/staging) informed a new Python candidate prototype. No PHP copied. Added manifest candidate creation, base-hash and revision checked staged snapshots, typed patch/work packet contracts, task/workspace binding and durable candidate events. Three fixture tests passed in 0.49s. This is not an integrated coding worker or activation system; caller serialization is provided by the Development service and cross-process fencing remains pending.

Current Phase 1 evidence: real Engine de0d65b8ed6746e6957d4cf123d95610 completed a narrow repair in 34.38s, test unchanged, local model unloaded. IAB isolated port 18976 verified folder registration, automatic scan, readable map/search/source, background setting disable and persistence after reload. Disposable restore drill restored 142 files and two SQLite databases with integrity ok (E:/AI/audits/restore-drill-20261107/result.json). This does not verify production activation.

Active temporary UI server: PID 8044, port18976, isolated root E:/AI/audits/context-ui-resumed-20261107; exec session72874. Stop only this owned server after remaining UI tests. No production restart. Full-plan implementation continues; do not mark phases 1–5 complete.


### Candidate execution and direct facade — 2026-11-07

- Added candidate_test with explicit revision, argv-based pytest, environment allowlist, bounded output, timeout/process cleanup, before/after hashes and durable evidence. This is trusted same-account execution, not an OS sandbox.
- Added candidate_diff against the original snapshot and validation that a manifest cannot redirect the revision directory. Local tools, authenticated HTTP routes and MCP registrations share Development; public connector deployment remains pending.
- Real Engine task 13617df2c83f4f0cb8da7020e1de4a8c used candidate_create/inspect/patch/test with Qwen3.5:4b in 31.03s. Test passed at candidate revision 1; original source and original test remained unchanged. Full action records were inspected. Final task state waiting_review; no activation. Evidence E:/AI/audits/candidate-live-20261107/acceptance.json. Ollama empty after unload.
- Latest focused run: 12 fixture tests passed in 5.58s (development API/workspaces/context integration). HTTP and MCP imports passed. Earlier broad run had 36 passes and one test-placement NameError; corrected, then reran affected tests successfully. This is not full QA/QC.
- APC attribution remains source/work separation and source-history hash contracts, implemented in Python; no PHP execution. Cross-process fencing, full work packets/guidance, Git candidates, UI development review, resource/model management, Guardian and public ChatGPT acceptance are still pending.


### Guidance and review UI continuation — 2026-11-07

- Added durable revision/consumer-epoch fenced task_guide/task_guidance_status HTTP/MCP paths. Guidance is included in fixed model context; receipt/in-packet events explicitly do not prove execution. Required-tool evidence gates finalization with bounded correction attempts.
- Real first guidance run dd022b291ab842d6a0e72ef05b289ef7 received guidance but skipped candidate_diff. Kept failure evidence. After adding explicit evidence requirements, run 32a4df880c3b48d1b61ae77eb3504888 used candidate_create/patch/test/diff in 41.56s, preserving live source/tests, waiting_review. Two recovered test selector errors are in full actions; runner now accepts validated file.py::test_function selectors (9 focused tests passed in 4.11s).
- Guidance/core/API tests: 33 passed in 18.90s. Model protocol/core/API tests: 31 passed in 15.56s. Protocol adapter accepts only whole-response, catalog/schema-valid legacy JSON tool envelopes, never calls extracted from prose.
- Qwen2.5-Coder7B benchmark failed as director: first run 8ef824d718624f87aafd924b38d498a2 emitted textual tool JSON (33.62s). Adapter run eef8221e6cfb49158c7ade238851b62e executed create/diff but skipped patch/test (10.91s). Neither is a success; model remains non-default. Both unloaded their model afterward. Do not compare failure timings as equivalent performance.
- IAB actual review on isolated port18977 displayed candidate revision, original objective and unified diff. Fixed RTL code rendering after screenshot inspection. Proof E:/AI/audits/candidate-guidance-verified-20261107/development-review.jpg. Guidance submission through this UI is still untested.
- Old isolated UI server8044/18976 stopped after identity verification. New test server PID15956, exec84297, port18977 uses candidate-guidance-verified audit state. Production unchanged.


### Browser evidence, Git and APC import continuation — 2026-11-07

- Extended existing embedded-browser input with frame-bound virtual move/drag, coordinate normalization, observed region references and an owned Qt widget-event drag backend. Windows physical cursor is not used by this adapter. Isolated runtime supports distinct API/CDP/IPC identity; production defaults are unchanged.
- Real Engine tests exposed hidden-renderer CDP drag timeouts and a model-context reducer that discarded region labels/geometry. Errors now retain exception type, uncertain pointer actions stop blind replay, and compaction preserves region identity. Practical drag acceptance is still pending; failed runs retained under virtual-pointer-{refs,active,qt}-20261107.
- Added shared Git status and clean-base worktree creation. Unborn/dirty repositories preserve work and explicitly require manifest candidates; no reset/force/automatic commit. Local, HTTP and MCP Git status use the same adapter. Public connector activation remains pending.
- APC raw-index import now distinguishes entity source_hash from explicitly declared file content_hash, normalizes term arrays, rejects unsupported non-file entities with reasons and reports provenance/conflicts. Source contract: pinned APC inc/project_map.php entity_hash/addDoc. This is partial typed import, not full entity-graph parity.
- Git-aware indexing honors cached/untracked nonignored inventory. Traversal is limited to 100,000 entries/30 seconds and reads to 100 MB; read/traversal failure rolls back index changes. Resumable chunks, watcher-based optimization and large-project performance acceptance remain pending.
- Tests: earlier full development regression 224 passed in 46.76s; subsequent focused Git/API/browser 10 passed in 4.15s; browser/APC/context 15 passed in 2.34s; visual-context/inventory/APC 4 passed in 0.92s. These are fixtures, not final QA/QC or release acceptance.
- Production was not restarted. All plan completion gates remain open where no practical evidence exists.


### Verified pointer and model catalog/resource continuation — 2026-11-07

- Real Engine virtual-pointer task 86b2fa745b1f481a829573eb373fcfed passed in 40.20 seconds; retest 59c66c53c40345e09998ad5a143e6537 passed in 38.77 seconds after timer release handling. Synthetic page independently recorded clicked and dragged; final waiting_review. Evidence in virtual-pointer-context-20261107 and virtual-pointer-release-timer-20261107/acceptance.json. Both unloaded the model. This supersedes the earlier pending drag result, not general browser compatibility.
- Full regression at that revision: 231 passed in 51.06s (regression-context-pointer-20261107/junit.xml). Later candidate cross-process lock/API tests: 4 passed in 1.56s. Model catalog/core/context: 28 passed in 16.53s.
- Candidate patch/test now hold a Windows byte-range writer lock across processes, released by OS exit. Activation/Guardian ownership is still pending.
- Added persistent Ollama download jobs, progress, cancellation/interruption recovery and explicit resume with shared local/HTTP/MCP services and readable installation controls. Downloads do not select/load models. IAB on isolated port18979 requested the already installed qwen2.5-coder:7b, observed installed/verified, and Ollama showed zero loaded models. Evidence model-catalog-live-20261107/ui-install-evidence.json and catalog-ui.jpg. This verifies cache/reverification, not a fresh multi-GB download or public connector.
- Added initial durable model resource ownership shared by inference, coding advice and memory control. Internal switch evicts only recorded managed models; unknown external resident models block admission. Explicit user unload/disable remains separate. Resource integration is under test; external GPU telemetry, hardware budget admission and queue fairness remain unfinished. Hugging Face catalog/install and Guardian remain unfinished.
- Model/download/resource components are native Hub code, not APC ports. APC typed file import provenance is stored in context_import_reports; unsupported schema/entities report explicit reasons.
- Temporary isolated API7172/18979 remains for QA; old isolated15956/18977 also remains. Production unchanged. Full plan is not complete.


### Scoped coding worker and indexing efficiency — 2026-11-07

- Added a short-lived patch-only Python worker process using installed models and structured output. No model-provided shell/desktop tools. Parent validates allowed paths, original hashes, candidate revision, task/guidance revision, preserves selected acceptance tests, stages changes and runs tests. Same-account process isolation is not an OS sandbox. Work packets are persisted with original objective, source hashes, constraints, guidance and acceptance tests.
- Shared candidate_repair is registered for local tools, HTTP and MCP. Review UI displays persisted test results with revision and output. Full immutable WorkPacket/activation contracts and public long-running MCP delivery remain unfinished.
- Service-level real-model microbenchmark: Qwen3.5:4b 6.56s and Qwen2.5-Coder:7b 6.28s, both exact tests passed with original source/tests preserved. Models were tested serially and unloaded; default unchanged. Evidence coding-worker-benchmark-20261107/benchmark.json. This is a narrow worker diagnostic, not broad Phase3 model selection or completion of the catalog delivery gate.
- Engine worker delegation test e23844df2a314b4d8cb566f850305e25 (29.69s) failed the requested execution path: model used candidate_patch/test instead of candidate_repair. Required-tools flag false; retained failure evidence coding-worker-engine-20261107/acceptance.json. A new required-worker run is in progress.
- New code tasks reuse existing index instead of forcing a full scan. First index still scans; source handles revalidate hashes and search includes snapshot identity/freshness. No watcher/chunked resume claim. A 20-project/400-file fixture scanned in 3.36s; scoped search/overview in 0.218s, no model (context-many-projects-20261107/result.json).
- Fixture results: resources/memory/core 30 passed in 15.11s; context/resources/memory 13 passed in 2.89s; scoped worker/API/memory 9 passed in 3.10s; latest worker/API/ownership 6 passed in 2.98s.
- APC contribution remains the documented source/work identity, context/index metadata and history contracts. Resource ownership/model installer/worker process adapters are native Hub implementations. No production restart, release or commit. Full plan still in progress.
### Development continuation — 2026-11-07: coding worker and Hugging Face

- Agent-owned required worker task 80f93df5db2248d19f9360ea7995be96 passed in 36.24s, using candidate_create/candidate_repair/candidate_diff with no tool errors. Original code/tests preserved; worker tests verified; final waiting_review, no activation. Evidence: E:/AI/audits/coding-worker-engine-required-20261107/acceptance.json. Supersedes pending worker acceptance, not full plan completion.
- Provider/catalog fixtures: 5 passed in 0.91s. Catalog/context integration: 7 passed in 7.12s.
- Actual IAB on isolated API18980 searched Qwen's public Hugging Face repository, inspected license/files, installed qwen2.5-coder-0.5b-instruct-q4_k_m.gguf (491400064 source bytes), observed installed/verified, and recorded zero resident models afterward. Evidence E:/AI/audits/model-hf-ui-20261107/installation-evidence.json and catalog-hf-ui.png. This is a fresh provider download, not a local model inference test. Production unchanged.


## 2026-11-07 — conversation continuity and ongoing product QA
- 34 conversation/model-context/core fixtures passed in 21.75s; 25 API/memory/Guardian/job fixtures passed in 11.13s. These are fixtures, not public connector acceptance.
- Real Qwen3.5:4b Engine recall: 22 seeded prior turns, required fact in turn 4 outside the latest-12 seed. Model called conversation_history and returned the exact Hebrew identifier in 9.19 seconds. Evidence: E:/AI/audits/conversation-memory-live-20261107/acceptance.json. Models unloaded afterward. This is narrow recall acceptance, not a year-long workload benchmark.
- IAB port18981: settings category navigation, safe Markdown display, memory dialog, pagination from10 to20 turns, saving continuity note revision1 and reopening with the same text succeeded. Proof: E:/AI/audits/conversation-memory-live-20261107/continuity-ui.png. Other menus and native browser remain under QA.
- Earlier scoped-worker context-window failure was corrected with task-scoped tool groups. Real task7c047b4cd97641a8b378dc83691400ee completed required repair/diff/tests in29.14s with original source/tests preserved (worker-tool-discovery-20261107).
- Guardian Engine acceptance819ebac5b4234192a6a9bec884e76a8f failed after81.98s; retry ef35dc80a8194657b93546b5fa4c14ff exceeded420s while repeatedly observing stale index status. Both are failures, not verified deployment. The direct-refresh status bug was repaired; a new isolated run is in progress.
- Full earlier suite252 passed/1 fixture failure in56.23s; settings fake-client preflight fixture corrected and focused tests passed. Full latest suite still required.

2026-11-07 continuation: Python compilation succeeded for browser extension/view/IPC callers, API, gateway and tool registry. Seven session-transfer/conversation-memory regression tests passed in 5.26 seconds. This does not validate extension lifecycle, browser visual appearance, Chrome import on a real account or public MCP availability.

- Nine memory-review, conversation-history and session-transfer regression tests passed in 6.03 seconds. Review coverage includes disabled default, persistence, missing-context downgrade, replay protection, cross-chat isolation and stale-source rejection. These are fixture tests, not ChatGPT acceptance.
- Qt extension installation returned a real installed/disabled record. Enabling a minimal Manifest V3 extension exited the isolated process with code 1 in repeated direct Qt and view-backed probes, before returning from setExtensionEnabled. Full lifecycle failed; shared enable action is blocked.
- Real Guardian Engine acceptance task 30fe4b6a36794af989245c96a343a5a3 exceeded 420 seconds, paused, repeated list_files after candidate_repair, and did not activate a release. Original source preserved; Ollama models unloaded. Evidence: E:/AI/audits/guardian-engine-statefixed-20261107/acceptance.json.

- IAB on isolated port 18981 saved optional memory feedback enabled with MCP preference and displayed the saved state. Proof: E:/AI/audits/conversation-memory-live-20261107/memory-feedback-ui.png. Registered MCP Python adapters made real HTTP requests to the same server, read those settings, submitted and retrieved a source-bound review; false context availability correctly produced unavailable. Evidence: memory-review-mcp-adapter.json. This is adapter/UI parity, not a fresh public ChatGPT connector test.

- Real memory-feedback Engine run b returned the correct name in 14.52 seconds and invoked both tools, but independent action-log inspection found the wrong source task in its review packet. This run is NOT accepted; independent-review.json corrects the weak tool-presence-only script verdict. Added exact evidence_quote validation and a source-excerpt acceptance check; rerun pending.

- Real local Engine memory-feedback run d completed in 26.11 seconds, recovered after a deliberately rejected mismatched source ID, requested review with the correct original Hebrew quote, and accurately reported pending MCP feedback. Correct answer and source packet were inspected independently; Ollama ended empty. Evidence: E:/AI/audits/memory-feedback-engine-20261107-d/acceptance.json. This verifies local retrieval/request/fallback, not an actual ChatGPT response. Latest seven focused memory/coding-worker tests passed in 8.43 seconds; preceding 14 API/coding/memory/session tests passed in 19.10 seconds.

- Full suite snapshot: 270 tests passed in 66.97 seconds. Later conversation-submit scalability changes separately passed 11 conversation/recovery/memory tests in 6.44 seconds and three history tests in 6.78 seconds. Full suite must be rerun after final remaining edits.
- Synthetic 10,000-turn storage benchmark retained all 10,001 turns after a new request: literal search 0.080 s, submit 0.110 s, DB 104,927,232 bytes. E:/AI/audits/memory-scale-20261107/benchmark.json. This measures storage/dispatch, not year-long model reasoning quality.

2026-11-07 Guardian real Engine acceptance: task cefcb9828d824ebaba204a7285828c23 reached waiting_review with patch-worker ACTIVE_VERIFIED, 174.69 seconds and 60-second stabilization; original source preserved, resident models empty. Evidence: E:/AI/audits/guardian-engine-syntaxretry-20261107/acceptance.json. This is an isolated patch-worker activation, not full-app production acceptance.

2026-11-07 Memory-feedback adapter verification: 8 tests passed in 4.05s covering prompt return of pending reviews, current deduplicated replies, and MCP functions using the authenticated HTTP service with shared persisted settings. Missing original context downgraded an attempted confirmation to unavailable; original history unchanged. This is adapter integration, not a live ChatGPT response.

2026-11-07 Full regression after memory source binding, chronological fallback, worker Python preflight and MCP review observation: 273 passed in 69.52s. The subsequently added authenticated HTTP/MCP integration test passed in the separate eight-test run (4.05s). No production deployment.

2026-11-07 Conversation viewport: 17 tests passed/20.11s (conversation memory and HTTP API). IAB isolated port18982 with 65 synthetic retained turns: observed pages35–64,5–34,0–4, expanded first-turn history_probe evidence sequence0, returned to35–64. Screenshot E:/AI/audits/conversation-pagination-20261107/history-oldest.png. This is UI history navigation, not new model recall acceptance. ServerPID7448/session11323 remains isolated. Initial attempt to share18981 state correctly failed the exclusive owner lock; new root used.

Decision anchors: first regression run19passed/1failed because the test attempted unsupported Store.update(goal); changed test to simulate external DB corruption explicitly. Rerun7passed/26.38s. Real Engine trial13.22+18.47+12.91s FAILED: wrong source ID rejected, zero cursor produced empty list, final falsely claimed missing history. Corrected current-task identity in continuity and zero-as-start cursor; real rerun pending. Models unloaded after failed trial.

2026-11-07 Real decision-continuity Engine acceptance passed: conversation-anchors-engine-20261107-b/acceptance.json. Three independent Engine turns took12.05s/9.56s/8.47s. Model stored the first exact user quote, linked a later correction after20 filler turns, then recalled both current and former names after another20 fillers from the saved source-bound anchors. Inspected actions confirm writes/read and supersession link. Both sources preserved, resident models empty. This proves this scenario, not arbitrary year-long semantic recall or public ChatGPT feedback. Focused conversation/MCP wait tests12passed/18.38s.

2026-11-07 Live ChatGPT memory feedback: in the user-authorized original conversation, Codex IAB sent a source-quotation review about the Notepad-window-only screenshot request. ChatGPT returned matching review_id, confirmed/context_available=true and explicitly limited its finding to the historical request. Saved raw reply, screenshot and verified persisted annotation in E:/AI/audits/chatgpt-memory-feedback-live-20261107. The shared parser/service accepted it and original history was unchanged. Transport was manual Codex IAB, NOT the local agent automatic browser dispatch and NOT public MCP acceptance. Correlation regression tests10passed/4.10s, including wrong/missing review ID, invalid boolean and non-object JSON.

2026-11-07 Real Engine feedback continuity: E:/AI/audits/chatgpt-memory-feedback-live-20261107/engine-continuity.json. Qwen used conversation_memory_reviews to read the actual IAB-acquired ChatGPT reply, returned window-only screenshot scope and explicitly said feedback does not prove desktop execution.14.66s, waiting_review, resident models empty. This verifies consumption of real feedback, NOT automatic outbound dispatch. Nine focused memory/history tests passed16.22s before the final status-refresh edit; UI feedback-history rendering and public connector remain unverified.

2026-11-07 IAB UI feedback evidence: isolated18983/PID23808 (session30352) using SQLite backup of the live-feedback audit store, not production. Opened memory/history dialog, observed confirmed feedback/exact source quote and expanded original-source content successfully. Screenshot E:/AI/audits/feedback-ui-20261107/feedback-source.png. User-facing history kept intact; no model loaded.

2026-11-07 Full regression after feedback history/context propagation, decision anchors, viewport paging and fresh final-review state:278passed/77.44s. No production rollout; automatic local-browser outbound feedback and fresh public MCP remain acceptance gates.
# Memory-feedback flag validation — 2026-11-07 (Unreleased)

Shared service rejects string/numeric/container values for context availability and enabling feedback; invalid replies preserve pending status and original source. `tests/test_memory_review.py`: 17 passed in 4.65s. `tests/test_api.py tests/test_dispatch_wait.py`: 20 passed in 8.15s. These are fixture/API adapter tests, not automatic live ChatGPT/MCP deployment acceptance. No production restart performed.

# Long-history retrieval and cursor integrity — 2026-11-07 (Unreleased)

Real Engine recall from1,000 synthetic turns and26 anchors FAILED (11.64s,10.91s) in conversation-long-recall-20261107 and conversation-long-recall-20261107-b. Source IDs/codes absent from initial packet; action logs confirm insufficient retrieval and unrelated acknowledgement, so neither result qualifies as success. Models unloaded after each. Generic guidance insufficient. Source-preserving cursor regression plus API/conversation/wait tests:26passed25.44s. Automatic public connector and broader continuity remain unverified.

# Indexed decision recall — 2026-11-07 (Unreleased)

Full regression after indexed retrieval/audit changes:297passed94.57s. Unit/adapter success does not override the independently observed d answer failure.

Audit-event retest d took14.88s and returned correct codes with logged source IDs, but independent answer review FAILED: final sentence invented removal of the correction. Evidence conversation-long-recall-20261107-d/independent-review.json. Verifier now reports retrieval_verified separately and leaves overall verified unset until independent review; keyword/source checks alone do not certify answer correctness. This semantic failure remains open.

Real Engine acceptance conversation-long-recall-20261107-c passed11.30s:1,000 synthetic turns,26 anchors, requested codes absent from recent-eight packet, automatic source retrieval supplied original and correction with source IDs, answer correctly identified both. No remote feedback used. Model unloaded. This supersedes failure for this fixture only, not all semantic continuity.47 focused conversation/memory/context/API fixtures passed27.29s, including correction-chain expansion when correction omits subject, chat isolation, stale source and existing-anchor index migration. Audit-event retest pending.

# Historical report provenance — 2026-11-07 (Unreleased)

conversation-long-recall-20261107-e:12.14s, real Engine used conversation_memory_reviews and conversation_history; final codes and source positions137/413 match actual records, independent-review.json passed. Original replies preserved. conversation-unanchored-recall-20261107:29.11s FAILED; phrases with Hebrew article differences returned chronological fallback, then model confused history reading with forbidden desktop input. Failure preserved and models unloaded.19 conversation/context fixtures passed17.40s;20 API/wait fixtures passed8.28s before schema-message wording change. Whole continuity/public transports remain incomplete.

# Unanchored request retrieval — 2026-11-07 (Unreleased)

Added native Hub FTS5 original-request index, migration/triggers, chronological exact+token candidate union and per-record source roles. No APC code reused.38 focused memory/review/API tests passed27.47s before role labels;20 conversation/model-context tests passed17.33s afterward, including exact later question not hiding older approximate sources, page traversal, chat isolation and source update.

Real Engine conversation-unanchored-recall-20261107-b retrieved correct IDs10.05s but independent review FAILED speaker attribution and language. c retrieved both IDs13.33s but reversed current/old in final answer despite quoting correct chronology. Both independent-review.json files reject overall success. Models unloaded. Next required work: validate claims against retrieved sources/chronology before finalization; do not continue optimizing retrieval alone or treating keyword hits as answer correctness. Public automatic feedback/deployment remains unverified.

# Local historical-answer review — 2026-11-07 (Unreleased)

Added bounded source-only extraction, exact quote/ID validation and up to three review attempts using the already selected model. Same-model review is not independent proof. Two real trials incorrectly approved reversed drafts; independent-review.json marks both failed (conversation-unanchored-review-20261107 and -b). Pure history tasks now review and return the separately source-derived answer instead. Real Engine -c26.51s passed independent factual review: correct current/former codes, original quotations, chronology and distinction between questions and corrections. Terminology still says attached documents instead of conversation sources. Model unloaded; no GPT contacted.23 latest review/conversation/context/wait fixtures passed4.00s;17 earlier review/API fixtures passed6.11s. No public connector or universal recall claim.


### PLAY connection development QA - 2026-11-07
- Focused bridge/transcript/protocol/API run:42passed12.27s, before final new-conversation endpoint/test. JavaScript syntax checks passed before the last UI refinement.
- Actual Codex IAB UI, isolated root E:/AI/audits/play-ui-20261107, API18984: observed empty dialog caused by detached controls; repaired shell initialization, reopened PLAY/MCP panels, added an isolated project, saved a synthetic ChatGPT URL with MCP preference and favorite, reloaded and observed all three persisted. This is UI/settings acceptance, not a connection to that synthetic URL.
- Public connector discovery still exposes seven older tools. New connection/memory tools are not yet accepted publicly. No production restart or model load. New-conversation setup and hidden-pane traffic still need actual native agent browser validation.

2026-11-07 latest validation: full regression306passed95.20s; subsequent focused bridge/API/protocol run43passed23.91s includes the newest new-conversation bootstrap fixture. Full-suite collection preceded that one added test. Both runs exited0. Actual automatic browser/public connector acceptance still pending.

2026-11-07 update: added native AI connection catalog/cards for ChatGPT (Web PLAY/MCP), with Claude/DeepSeek explicitly not implemented. Reviewed APC browser/local-bridge candidates in docs/APC_BRIDGE_REUSE_REVIEW.md and manifest; no bridge code port claimed. Latest44 focused tests passed13.00s before connector catalog addition. Live isolated PLAY setup reached loading/not-ready error; fixed visible opening/attention status and45-second setup bound. Signed-in native bootstrap remains unverified.

## Browser chrome and connection QA — 2026-11-07 (Unreleased)
58 focused tests passed in 16.51s: API, browser UI queue, ChatGPT bridge, PLAY protocol, bridge transcript, browser input and DOM. JavaScript syntax and Python compilation passed. This is not a new full-suite result.
Offline Qt fixture used the real BrowserView under an inherited dark parent stylesheet; widths 480 and 820 verified painted light chrome, in-bounds toolbar controls and retained menu actions. Artifacts: E:/AI/audits/browser-chrome-20261107/chrome-480.png, chrome-820.png, render-evidence.json. These are offline widget renders, not live desktop or website acceptance.
Actual Codex IAB checked QA port 18984: selecting the ChatGPT tab updated the live frame/address after the serialization repair; a 700px viewport showed the model name on one line; the login-required probe remained visible during polling. Screenshots: sidebar-700.png and play-login-required.png in the same audit directory. Viewport override was reset afterward. The isolated native window was shown using the product browser control. Signed-in PLAY bootstrap/ACK and public MCP acceptance were not performed; the isolated profile is logged out. No production restart or new APC bridge code integration.

2026-11-07 saved-tab restoration:31 bridge/transcript/PLAY tests passed6.00s. Added fixture proving existing-tab login/loading failures raise the observed reason and show the existing tab rather than report successful restoration. This is regression evidence, not live authenticated PLAY acceptance. Production unchanged.

2026-11-07 uncertain handoff continuity:50 bridge/transcript/protocol/API tests passed13.31s. Fixture persisted an uncertain send, stopped/reloaded controller, attempted chat switch and new listen, verified both blocked before browser access and retained state/transcript. Original context remains accessible. Live authenticated acceptance remains pending.

2026-11-07 full regression completed:315 passed85.35s, exit0 (session6559). Actual IAB after user login: connection probe changed to ready. Clicked new PLAY conversation; observed sending state. Delivery/remote reply not yet verified. Transport tab selection was also observed updating saved-route selector in IAB. Production unchanged.

2026-11-07 actual PLAY bootstrap: after user login, IAB probe ready; new conversation sent instructions and displayed actual ChatGPT acknowledgment (12:38:47). Screenshot browser-chrome-20261107/play-live-bootstrap.png. Additional local conversation appeared during temporary-to-final remote URL transition; linking/deduplication gate remains open. No computer-action/hidden-pane success claimed.

2026-11-07 provisional URL fix:32 bridge/transcript tests passed6.92s. Fixture tests same-tab + matching new outbound message, rejects unrelated text/other tab, preserves pending text and restores permanent binding from disk. Full315-test run preceded this edit. Live bootstrap previously exposed duplicate local chat; post-fix live repeat required.

2026-11-07 post-fix live PLAY attempt failed before submission (busy or unsent draft). No pending outbound message recorded. Existing draft preserved/no resend. Screenshot E:/AI/audits/browser-chrome-20261107/play-draft-blocked.png. This does not verify provisional URL migration; it remains a release gate. Isolated API now5744/18984, native profile retained, production unchanged.

2026-11-07 preflight diagnostics:51 bridge/transcript/API tests passed13.63s;26 bridge tests passed5.59s after final metadata correction. Fixture verifies draft vs generation rejection before composer access, no pending send, not_sent classification, and preservation of uncertain status for submission timeout. This is fixture evidence; live duplicate-chat acceptance still pending.

2026-11-07 probe metadata follow-up:44 ChatGPT bridge/API tests passed12.44s; JavaScript syntax passed. Actual IAB screenshot play-existing-bootstrap-draft.png shows retained bootstrap-looking draft, not successful delivery. No draft altered. Live recovery acceptance remains open.

2026-11-07 draft provenance fixtures:34 passed6.54s. Exact complete local outbound draft resolves source chat/message/status; prefix, human message and modified text rejected. Read-only lookup, no browser mutation. Live draft ownership has not yet been queried with updated QA imports.

2026-11-07 actual IAB provenance probe: authenticated homepage draft blocks send; no generation active; exact local outbound match absent (draft_source null). Screenshot play-draft-probe.png. This refutes treating the observed prefix as sufficient ownership evidence. No clear/resend; live PLAY recovery still incomplete. QA API26856/18984.

2026-11-07 reversible draft service:19 draft/API fixtures passed7.74s; JS syntax passed. Fixture archives Hebrew text, restores it, prevents overwriting a current draft and retains saved copy. No live recovery or public MCP claim.


## PLAY draft recovery — 2026-11-07

Two draft fixtures passed (0.65s); app.js syntax passed. In isolated IAB UI on port 18984, archived 23,342 characters before clearing; the initial fill selected but did not erase text. Targeted unchanged-draft fallback then verified empty composer. Restoration retained all text but added six newline characters (two runs of three), so exact verification correctly failed. Archived restored content and verified clearing again. Original copies retained. Production untouched; full PLAY task roundtrip remains pending.

Live new-conversation PLAY after recovery: IAB confirmed listening and durable final conversation URL ending 593247d2331b after reload (temporary local-chatgpt URL resolved). Screenshot: E:/AI/audits/browser-chrome-20261107/play-linked-final-url.png. Stale probe warning is hidden while listening. Full task execution roundtrip still pending.

## Idle PLAY browser access — 2026-11-07
21 focused browser-access/draft/API tests passed in8.29s. Real IAB isolated18984: refreshed frame, selected connected tab, clicked composer, typed and sent a read-only browser_tabs request while PLAY remained enabled. Local transcript confirms user request at12:54:09. Browser pane hidden during processing. Task/result acceptance pending.

PLAY live acceptance exposed an absent initial cursor in empty conversations. Fixed bootstrap receipt anchoring and old-session fallback.28 bridge/access tests passed5.52s, including existing missing-cursor anti-replay regression. Previously consumed action was not replayed; submitted a new read-only request through IAB for live verification.

After cursor fix, a fresh user request was recognized and queued while pane hidden. ChatGPT instead used its installed MCP connector and reported Local Agent unavailable; isolated QA database correctly contains no task for that remote call. PLAY protocol v2 clarifies route ownership.1 protocol test passed0.25s. Revised live roundtrip remains pending; no complete acceptance claimed. Screenshot E:/AI/audits/browser-chrome-20261107/play-transport-collision.png.

## PLAY signed-in acceptance and repairs — 2026-11-07
Live protocol v2 acknowledgment succeeded in the existing conversation. Actual task 9c16c33407eb4243b40acfc9c6ee0b41 failed before tools due catalog context overflow. After desktop catalog reduction, task 373ad553ef3443708054c4946e105032 called browser_tabs three times and observed seven tabs, but its completion gate misread a prohibition as a close request. No close action occurred. Fixed negation and proposal handling. Transport recovery also needed generic-error receipt reconciliation and consumed-reply idle restoration. 34 core/context tests passed16.87s; 39 close/bridge tests passed7.59s; subsequent32 bridge tests passed7.89s. Full332 tests passed89.00s before the last recovery changes. Production and public MCP remain unchanged. Real successful end-to-end result delivery still pending.

Full335 tests passed102.49s before the keyboard-submit adjustment. Task cb7d881aca6648ab8fca4558b5f5f04a returned seven tabs after one browser_tabs call, but automatic feedback remained a draft and delivery was correctly uncertain. Existing draft submitted once through observed IAB UI for recovery; this is not automatic end-to-end acceptance. New keyboard-submit adapter:32 bridge tests passed7.70s.

Automatic PLAY result delivery verified: task708dccf24c7c49d2819ade085bb2a339 ran browser_tabs once, returned7, and persisted chatgpt_delivery sent=true with new message4937b254-a6c8-44b8-a49d-8c1af105605b. Independent IAB inspection of the linked conversation confirmed automatic result and ChatGPT answer7; no manual send for this task. Task execution4.17s. Evidence E:/AI/audits/browser-chrome-20261107/play-automatic-result.json and .png. Local listener remained waiting_reply despite remote answer; added safe idle refresh for waiting_reply and frame-only viewing (35 tests passed8.44s), recovery verification pending. This proves this read-only task roundtrip, not all PLAY/memory requirements.

2026-11-07: Grouped-message PLAY mapping live-verified on isolated API18984/PID23880. Task708dccf24c7c49d2819ade085bb2a339 automatically delivered result7; after mapping fix runtime last_reply=7, phase=listening, error empty; IAB tab12 showed the same answer and listening badge. Evidence: E:/AI/audits/browser-chrome-20261107/play-automatic-result.json. No manual result send for this task. Earlier manually recovered task is not counted. Latest focused tests35passed7.79s; full regression session90336 running. Native Hub implementation, no APC port.

2026-11-07: Live task ef3e9200def345ca8890fe740bd23c50 read source result7 and invoked conversation_memory_review. Browser ChatGPT returned correlated review458e2235220847a3b9c7d50f26280530, confirmed with accessible historical evidence in12.90s. Subsequent local answer-review distorted the feedback; this is NOT complete task acceptance. Saved memory-live-result-b.json. Added deterministic memory-only feedback reporting and explicit assistant-report source retention;28 focused tests passed8.35s. Earlier full337 passed91.63s predates these changes.

Live retry37f186b1db8d476f81e1489b0f86acc6 retrieved the correct saved browser review but final validation failed because saved-review evidence was omitted from the reviewer packet. Fixed evidence retention and added history/order regressions;30passed4.66s. New isolated Engine task a2d0ccfbe7ab4998b8d8a3483fe20176 running against API18984 PID22516/session28760.

2026-11-07 real Engine acceptance d: a2d0ccfbe7ab4998b8d8a3483fe20176 completed execution in24.84s (waiting_review). Exactly conversation_history then conversation_memory_review; final text preserves confirmed feedback, exact source7 and remote evidence, explicitly disclaims current-machine verification. This reused the correlated saved browser response from the earlier live consultation, not a second remote send. IAB displayed the same final text and listening status; evidence memory-live-result-d.json and memory-feedback-success.png. Production unchanged; arbitrary recall and public MCP acceptance remain unproven.

Full current regression:345 tests passed88.66s, session60964 exit0. Includes latest feedback/history report fixes; real acceptance scope remains the isolated scenarios above.

## Project binding / PLAY continuation acceptance — 2026-11-07

Full regression after the final code changes: `python -m pytest -q`: **352 passed in 96.25 seconds**. Tests include same-chat candidate continuation, cross-chat rejection, desktop/API parity, exact file paging, manifest compaction and feedback receipt reconciliation. This is regression evidence, not full product QA.

Real agent task `5f50adce769d45a5b675d1486fa11080` used read_file, tools_enable and project_bind, preserving the chat and changing future workspace to local-agent-hub. Task `7d9a370c25bf4495a37f70a15f4d4af7` used candidate_create and created isolated candidate `27873bf626e64134b65416ad48c11a1d` (233 files). Subsequent failed tasks exposed context-size and cross-task ownership issues; these were fixed rather than counted as successes. Live continuation task `519a0e529fb44622982e250c38872df2` has been observed running via actual MCP `get_task`, with successful candidate_inspect actions. Final outcome is recorded in `E:/AI/audits/browser-chrome-20261107/resumed-task-mcp.json`.

IAB verified the enabled project selector and persisted project selection. Evidence: `project-binding-interface.png` in that audit directory. Actual MCP call_tool forwarded to HTTP on port18984 and candidate_inspect returned HTTP200. The externally connected public MCP still points to a different instance; public deployment/parity is not claimed. No production activation, commit or release was performed.

Follow-up: the live 4B run initially repeated tool enabling/inspection because only its latest tool group fit inference input. A bounded factual ledger of successful tool names now survives context compaction without changing the original objective or durable history; candidate Git detail is summarized separately. After reloading and resuming the same task, actual candidate_read and paginated read_file calls completed and task519a0e529fb44622982e250c38872df2 reached waiting_review. This verifies resumed execution, not the correctness of every claim in its generated summary or completion of the entire development plan. PLAY result evidence now also includes candidate/project/context tool results.

### Supervised code execution — 2026-11-07
The shared PLAY/MCP director contract now assigns map retrieval, task decomposition and evidence review to the supervising model. It requests focused indexed sources/related tests and delegates candidate repairs to the configured coding model. New MCP `coding_model_settings` reads/changes the same persisted coding model as the UI without replacing the general/vision model. In the audit instance the previous coding_model was empty; it is now saved and read back through MCP as `qwen2.5-coder:7b`. This confirms configuration, not yet a completed Coder repair. Candidate/project/context actions are included in PLAY feedback. Resuming an existing handoff restores its authorized objective if pause handling had cleared it.

Regression run after context/progress fixes: 353 passed in92.35s. Subsequent supervision changes:52 focused tests passed, one protocol ordering assertion failed and was fixed by retaining the original transport rule first; the protocol/API rerun passed3 tests. Final combined verification follows. Public MCP deployment remains unverified.

Final checkpoint for this repair: full suite353 passed in96.35s; after the last catalog-focus change,8 binding/protocol tests passed in4.26s. Desktop-dispatched coding now exposes the development catalog without unrelated UI schemas; explicitly enabling desktop/browser groups restores those tools. Live resumed task c6d725a36a134b708a3e8dd1e6528f9f observed missing index, ran context_refresh (234 indexed files), and then context_search returned source references. Evidence: E:/AI/audits/browser-chrome-20261107/map-resumed-mcp.json. This is actual local agent execution observed through the local MCP facade, not a claim that the entire delegated development task or public connector deployment is finished.

### 2026-11-07 PLAY preparation recovery
- `pytest tests/test_chatgpt_bridge.py tests/test_project_binding.py -q`: 44 passed in 9.58s. Includes preparation-only recovery and rejection of changed/partial drafts and post-submit retry.
- Live isolated instance 18984: completed mapping task c6d725a36a134b708a3e8dd1e6528f9f feedback appeared in linked ChatGPT conversation; bridge advanced to waiting_reply/submission_started. Director continuation still under observation. Public MCP deployment not updated by this check.

- Linked ChatGPT reviewed the mapping, rejected unsupported local-model claims, and emitted step 009. Real local MCP then returned task 07961d751a55479385f8351c77144086 running with completed project_index_status/context_search actions. Evidence: E:/AI/audits/browser-chrome-20261107/play-continuation-mcp.json and play-feedback-recovered.png. This proves continuation, not completion of candidate repair or the full development plan.

- Full regression suite after PLAY recovery changes: 357 passed in 92.10s. This is automated regression coverage, separate from the live continuation evidence above.

### 2026-11-07 failure feedback and lookup continuity
11 model-context tests passed in0.12s.40 bridge tests passed in9.10s, including failed/waiting_user/waiting_desktop feedback retaining the original objective. Prepared an independent URL-validation acceptance test in isolated candidate27873bf626e64134b65416ad48c11a1d revision1; source unchanged. Asked linked ChatGPT director to run it through the agent, then direct Qwen2.5-Coder repair with read-only tests. This is acceptance preparation, not completed model repair.

2026-11-07 supervised self-repair follow-up: full suite initially 360 passed / 1 failed (legacy missing action_id). Fixed fallback and updated recovery test to assert actionable feedback and no uncertain-action replay; 45 focused passed17.71s; full361 passed93.88s. Subsequent resource warm-handoff regression:4 passed1.26s. Real PLAY step010 ran four failing URL tests; director issued step011 candidate_repair using qwen2.5-coder:7b. It failed before edits because primary warm model was unregistered. Error returned automatically; director issued diagnostic steps012/013. Audit runtime restarted with fixes, explicit primary load verified. No completed source repair or public MCP deployment asserted yet.

Further validation:363 full tests passed100.72s before the final no-op/director-yield changes;31 focused engine/worker tests then passed20.75s. Real Qwen2.5-Coder loaded alone (5.47GB VRAM), produced unchanged source twice; revisions2/3 failed4 and passed8. These are explicitly failed attempts, not successful repairs. Original acceptance test unchanged. Added no-op rejection and immediate director return; runtime PID23964 loads these fixes.


### 2026-11-07: observed ChatGPT/Qwen self-repair acceptance
Real Web PLAY step 014 used Qwen2.5-Coder 7B to fix BridgeTranscript.link URL validation in isolated candidate revision 4. Model time 44.33s; acceptance and existing tests: 12 passed in 2.44s. Independent hash checks confirmed protected tests unchanged. ChatGPT received actual diff/results, requested read-only review step 015, then accepted the isolated repair for Codex integration review. Evidence: E:/AI/audits/play-ui-20261107/self-repair-acceptance.json and director-review-complete.png.
Codex integrated only the hash-verified source change and independent acceptance fixture into shared source. No production deployment or public MCP parity is claimed. Earlier full suite: 366 passed in 94.48s; post-integration full regression is being recorded separately.
Fixed global evidence compaction: diff changed-file counts and bounded path summaries survive omitted patch bodies; omitted changes no longer appear as an empty files list. Focused model-context regressions: 12 passed in 0.11s. These are native Hub fixes, not copied APC components.
Remaining: production activation, public MCP end-to-end parity, full Guardian upgrade/rollback acceptance and broader implementation-plan/UI QA. The full plan is not complete.

Post-integration regression: 371 passed in97.03s. Director review step015 actually called tools_enable, candidate_inspect and candidate_diff; it accepted the previously recorded 12-test repair result, but did NOT run a separate candidate_test/candidate_read. Do not describe it as a second independent test run. Codex subsequently ran the full shared-source suite.

2026-11-07 Git acceptance (in progress): user authorized MellowYAK/MellowCodex publication and subsequent validated-change commits. Agent preflight initially repeated filtered empty ls-remote output; paused that read-only task, supplied precise director guidance, and a second agent task observed REMOTE_EXIT=0 REF_COUNT=0 with credential.helper=manager. Global shell evidence guidance now recognizes legitimate empty listings and asks for one explicit count/exit check instead of repeated filters. Publication rules added to AGENTS.md; .gitignore excludes runtime secrets/databases/profiles/artifacts. No push success asserted at this checkpoint.


### Git publication and runtime recovery — 2026-11-07
Agent task d013a2a334d343718be75384e29ef44e performed the initial commit and push to https://github.com/MellowYAK/MellowCodex, branch main, commit b535fb37f8d3181914d3142e7de6993cdf8779f7. Its command output confirms matching local/remote HEAD and clean status. Codex reviewed 239 staged blobs (1,714,965 bytes) before publication; no scanned credential patterns, sensitive extensions or oversized files were found. This was supervised execution with explicit director commands, not an unsupervised Git benchmark.
Audit runtime 18984 restarted as PID23984 with current evidence-compaction/shell-guidance fixes. PLAY restored connected/listening with no pending outbound replay. Agent task af144d8db2d343278a4afb6f4a24771f then executed project_git_status and one run_shell status check, correctly interpreted empty output as clean and completed without the earlier loop. 14 focused Git/model-context regressions passed in2.84s after the shell guidance edit. Production/public MCP services were not restarted or upgraded.
Native Hub changes; no APC code imported in this checkpoint. The wider technical plan, public connector parity, full Guardian deployment/rollback acceptance and UI QA remain incomplete. Future completed validated changes are to be committed/pushed by the agent under AGENTS.md publication rules.


2026-11-07 public MCP Git acceptance: task 6d06fb7c5f94424e9cd7194a78f39178 executed run_shell through the public connector and returned equal local/remote main hashes b618f0699ec6fc1bc01e7f300bb8f6ae083e7e1b, exit 0, clean status. This verifies actual public-MCP Git read access. Initial attempt in an older conversation was rejected before execution with HTTP409 because an unrelated prior action remained uncertain; that history was preserved. The read-only Git test used a separate persistent Git conversation. This does not establish discovery of all new development/memory tools or autonomous repair/deployment parity.


## 2026-11-07 — source-first versus APC baseline (development, not released)

Independent Git/AST reference for Ember Video: 774 tracked files, 310 eligible text/source files, 215 Python files and 1,689 Python function/class declarations. Fast index after removing the 1 MB source exclusion: 310 files, no missing/extra paths and no hash differences. Existing syntax error in ember_video/install_qwen.py is retained as syntax_error, not represented as successful parsing. Evidence: E:/AI/audits/ember-map-comparison-20261107/fast-comparison-no-size-exclusion.json.

IAB at isolated port 18985 verified selecting Fast source exploration, persisted selection after reload, searching render_storyboard and opening the real gateway.py source. This exposed a stale map after refresh, subsequently fixed. MCP registration/HTTP fixture validates both mode changes and readback; this is not proof that the public connector is deployed.

Live Qwen3.5:4b Engine trials 01–03 timed out at 150–180 seconds without a final plan; trials 04–05 were stopped after 54/47 source actions without convergence. All remain in E:/AI/audits/ember-fast-20261107/acceptance*.json. No Ember application changes, downloads or media jobs were authorized or performed. Passing index equality is not passing autonomous project understanding. Trial 06 returned a plan in 224.70 seconds, but independent review rejected inaccurate API/worker claims. Trial 07 stopped after 131.82 seconds following three malformed source-handle calls; its intermediate model summary also inferred absence from unread source. Replaced inferred checkpoints with recorded excerpts and added exact indexed-path reads. Trial 08 is in progress; no autonomous parity claim.

Regression: 377 tests passed in 101.55 seconds before the large-source and final focused-packet changes; subsequent context/index/MCP/model-context focused set passed 33 tests in 10.62 seconds. A >4 MB streaming/tail/dedup test also passed. Further verification and agent acceptance remain in progress. New fast workflow is native Hub implementation; it imports no additional APC code.

Trial 08 failed at 27.03 seconds because added source evidence exhausted the inference packet; bounded the supplementary excerpt packet and launched trial 09. Full suite at this checkpoint: 384 passed in 107.43 seconds; subsequent path/cursor focused checks: 21 passed in 10.04 seconds. Public services remain unchanged.

Trial 09 ended incomplete at 238.80 seconds: the model used the intuitive path argument while the older running schema still required ref. The shared local/HTTP/MCP schema now accepts exactly one of ref or path, verified by the registration-to-HTTP fixture. Trial 10 runs the corrected schema and source continuation logic. 26 focused checks passed in 7.07 seconds after those changes.

Trial 10 exposed a controller KeyError after 62.43 seconds when continuing a path-based read. Normalized path/ref identity using actual returned references and added a path-based continuation regression; trial 11 follows. This failure is not an indexing coverage failure and is not marked successful.

Trial 11 was stopped after observing a pagination cycle: the continuation controller considered only the latest matching page. A regression now verifies interval union across earlier pages, including path-based reads. Its isolated model context changed from 16K to 32K during the run, so it is not a fixed-setting timing benchmark. Trial 12 uses 32K from the start; observed GPU allocation was approximately 5.7 GiB out of 8 GiB with one local model. Full suite before the final prompt-prefix/search edits: 388 passed in 103.00 seconds. Subsequent focused source/search checks: 16 passed in 7.41 seconds; model-context checks: 15 passed in 0.14 seconds. Agent understanding acceptance remains pending.

Trial 12 ended incomplete after 337.49 seconds following a read-only shell timeout. It exposed a separate 300 KB generic read_file cap; generic text reads now stream bounded character pages without that file-size exclusion. The local answer review now receives full selected source ranges rather than shortened text labelled as a complete range. Trial 13 returned an empty draft after 34.73 seconds; mutable evidence at an assistant-prefill position was corrected to a clearly labelled runtime user message, and empty answers are rejected without another model review call. Trial 14 was stopped after observed source-lookup drift; filename and distinctive measured AST symbol queries now prioritize their actual source definitions over incidental localized mentions. These are native Hub changes, not additional APC imports.

Checkpoint verification: 392 tests passed in 102.27 seconds before the final empty-response and search-ranking edits; 32 focused tests passed in 7.33 seconds after the empty-response fix, and 19 context-mode tests passed in 8.17 seconds after filename/symbol ranking. Trial 15 is a fresh read-only actual Engine run with Qwen3.5:4b, 32K context and no GPT feedback. Its outcome is not yet accepted; production/public MCP has not been restarted or deployed with these changes.

Subsequent full regression: 394 passed in 104.72 seconds. Named-function cursor regression initially exposed a padding mismatch (3 versus the established 5 lines), corrected; 20 focused tests passed in 8.66 seconds. This does not validate the pending actual agent investigation. Its repeated broad lookups exposed incidental-source drift; a separate regression now covers tracing the strongest already-read implementation before unrelated matches.

Trials 15/16 were stopped and recorded as unaccepted after observable lookup drift (unrelated voice implementation and diagnostics/relay source respectively). Added component-aware lookup for guessed compound identifiers, with an explicit heuristic notice; observed Ember lookup now returns image/video implementation and tests instead of diagnostics. 22 context-mode regressions passed in 9.79 seconds; 15 model-context tests passed in 0.10 seconds. Trial 17 runs the updated workflow against the unchanged original task; no per-project file list or expected plan is injected.

Full regression at that checkpoint: 397 passed in 111.82 seconds. Trial 17 exposed missing from-package module relationships and a draft falsely assuming native text-only video support; local consistency review rejected that draft. Fast extractor now records from-import module candidates and prioritizes concrete modules over package markers, with unchanged baseline bytes verified in a regression. 23 context-mode tests passed in 10.51 seconds. This is a fix to source relationships, not a claim of full cross-language semantic analysis or successful final agent acceptance.

Trial 17 stopped unaccepted after 300.57 seconds. Trial 18 used installed Qwen2.5-Coder 7B at 32K context, automatically replacing the managed 4B model; Ollama reported only the coding model resident. It returned an unverified plan after 127.84 seconds without source-tool calls beyond startup instructions. Added a model-selected-concept/source-grounding startup phase using the same runner and action log. 29 focused mode/integration checks passed in 13.11 seconds; 44 indexing/inventory/integration/mode checks had passed in 18.20 seconds before this startup addition. Trial 19 tests the new startup with the same original read-only task and coding model. No GPT feedback, Ember edits, public deployment or successful parity claim.

Trial 19 returned unverified after 146.62 seconds: its search concepts selected voice-related sources instead of the image/video implementation. This is a failed understanding acceptance, despite actual search/read/related actions. Trial 20 returns to Qwen3.5:4b with the same new source-grounding startup. Model selection changes remain confined to the isolated audit state; production settings are unchanged. Current-window screenshot requested by the user was captured separately; its existing PLAY page load error is not the transport used by these local Engine trials.

Trial 20 was stopped unaccepted after broad concept searches prioritized generic documentation. Fast search now removes generic query boilerplate when distinctive terms exist and ranks matching implementation basenames without excluding other matches. 25 context-mode checks passed in 11.21 seconds; full regression subsequently passed 400 tests in 112.59 seconds (regression-latest.txt). Trial 21 is a fresh actual Engine run with the unchanged read-only task: it reached text/image and image/video implementations, UI, validators and tests, but its first draft incorrectly claimed complete text-only video support. The local reviewer rejected the draft but supplied misleading secondary objections based on partial excerpts. Added general input/output-contract comparison guidance and focused review priorities after that observation; these final prompt changes are not included in trial 21's already-loaded code. No independent understanding acceptance, public deployment or publication is claimed.

Trial 21 subsequently repeated a literal decorator lookup using bag-of-words results. Added exact call/decorator matching before token fallback in Fast only. 26 focused context-mode tests passed in 11.83 seconds; direct adapter lookup of the observed decorator found ember_video/image_video.py at line 162. This proves source navigation behavior, not the model's final interpretation. git diff --check passed (existing line-ending warning only).

Trial 21 reached the audit's 600-second deadline (600.10 seconds) without a valid final answer and was cancelled by the harness. It is an unsuccessful understanding test, retained in acceptance-21.json. Full regression after contract guidance and literal lookup: 401 passed in 110.67 seconds. Trial 22 uses installed Qwen2.5-Coder 7B with the same task and updated shared workflow, confined to the isolated audit settings. Results remain pending.

Trial 22 returned after 61.86 seconds, but independent review rejected its vague/incorrect attribution of conversion implementation to frontend JavaScript. A strict all-term search had excluded strong implementation-filename leads when an additional descriptive term appeared. Corrected that filtering and reserved startup reads for later concepts; 27 focused tests passed in 11.90 seconds. Trial 23 reached improved source results, but ended unverified after 122.75 seconds. Its local reviewer incorrectly treated text_image_service.py as nonexistent because it was absent from the selected excerpts; the file does exist in the project. This is a remaining review-grounding defect, not evidence of a missing source file. Neither trial establishes Codex-level project understanding. No Ember source changes, production rollout or Git publication occurred in this checkpoint.

Added agent-owned draft reference grounding through logged context_search/context_expand calls, basename-aware review selection and an explicit observed-file inventory. Trial 24 (75.28 seconds) actually found/read text_image_service.py, fixing the earlier absence error, but independent QA still rejected its conflation of text/image and video capabilities despite local reviewer approval. Added same-directory cross-extension companion candidates (hyphen/underscore normalized), marked filename_heuristic, and frontend-to-companion reads before final review. 29 focused checks passed in 12.44 seconds; an additional real-dispatch fixture verifies frontend and backend source reads and no repeat reads (1 passed in 2.16 seconds). These are native fast-mode changes; APC baseline remains separate. Fresh actual acceptance and full regression remain pending.

Full suite at the reference-grounding checkpoint: 404 passed in 115.89 seconds. A separate targeted inference diagnostic with API/worker source recognized the mandatory source asset with thinking disabled (26.37 seconds); thinking enabled was slower (78.69 seconds), truncated at 4096 tokens and included an incorrect validator statement. No production reasoning setting was changed; this diagnostic is not agent acceptance. Trial 25 exposed deterministic recursive graph drift: repeated searches consumed the latest dependency list rather than original search results. Stopped only its owned audit processes and recorded cancelled status after 254.88 seconds. Corrected root anchoring/prefix coverage and withholding rejected drafts from future inference while retaining the complete model-event log. 59 focused context/core tests passed in 31.27 seconds. Trial 26 uses the same original task with Qwen3.5:4b and these corrections; not yet accepted.
# Resource-aware development checkpoint — 2026-11-07

61 context/core fixture checks passed in 34.18 seconds, including two external-controller pause/cancel cases. Expanded filename-ranking regression passed separately in 1.74 seconds. Direct Ember index query `text-to-video worker process` now ranks `ember_video/image_video_worker.py` first; this is adapter evidence only. Actual trial 26 was already running older ranking code and remains unaccepted. Only Qwen3.5:4b was loaded in Ollama (4,109,379,828 VRAM bytes); no 7B model was resident. GPU total usage was 5,742/8,192 MiB and 100% utilization during inference. Further acceptance uses the smaller installed model; no concurrent heavy model loading.

Full regression after filename ranking and external task-control guards: 408 passed in 111.62 seconds. After passing observed project context into source-navigation planning: 31 context-mode checks passed in 13.40 seconds. Trial 26 was stopped and recorded as unaccepted to avoid continued GPU use on superseded ranking; unloading was observed with an empty Ollama model list, GPU 1,049/8,192 MiB and 0% utilization. Trial 27 uses the new ranking but predates the navigation-planning context fix; still pending independent acceptance. No public deployment or parity claim.

Hash reuse validation: 40 project-context/context-mode tests passed in 16.90 seconds. Actual Ember repeat refresh indexed 310 unchanged files with zero extraction calls in 0.5309 seconds; evidence hash-cache-verification.json in the fast audit folder. Trial 27 was cancelled through a separate Engine controller and exited cleanly after inference (226.32 seconds), verifying persisted cancellation instead of overwriting it. Trial 28 (234.65 seconds) remained trapped in conversation-history lookups and was cancelled, not accepted. Fresh-conversation evidence framing is being corrected; no successful independent understanding claim.

After hash reuse and fresh-chat framing, full regression passed: 411 tests in 113.28 seconds. Trial 29 stopped at 305.42 seconds without a final answer; it no longer called conversation_history but still repeated broad source discovery. Added explicit read-only draft synthesis with source-grounding/review retained; 63 context/core checks passed in 34.37 seconds. Trial 30 is the actual Engine test of this workflow, still using Qwen3.5:4b without GPT feedback. The classification does not authorize mutations or bypass review.

2026-11-07 incremental-cache follow-up: 42 context/mode tests passed in 18.15 seconds. Added an explicit same-size, preserved-timestamp content edit regression; the cache regression passed in 1.56 seconds. Ember refresh evidence (`hash-cache-verification.json`, audit-only) recorded 310 unchanged files, zero changed/deleted/skipped files, no parser calls and 0.530872 seconds. This is direct adapter evidence; actual Engine search results also report snapshot revision 29 with 310 unchanged files. Full source-understanding acceptance remains separate and unaccepted. Trial 31 produced drafts with unsupported storage/API assumptions and returned to broad search after named-source grounding. Added immediate read-only draft revision after grounding/review, retaining observed sources and treating critic feedback as derived rather than authoritative. No implementation request is converted to read-only synthesis.

Trial 32 completed in 150.83 seconds with waiting_review, not accepted: the same local model still made unsupported project-wide absence/capability claims. Its focused draft revision reduced broad-search loops but temporarily removed source tools from the revision pass, preventing a needed lookup. Source-only tools now remain available during that pass (project map/search/read/relationships); a runner regression verified that a rejected draft can request a missing source and then correct the answer. One focused regression passed in 2.11 seconds. Trial 33 tests this with the same original objective, 4B model and no GPT feedback. These remain native Hub changes, with no new APC code imports or production deployment.

2026-11-07 native fast follow-up: 34 context-mode checks passed in 14.73s after fixing navigation-tree budget pressure on the last source excerpt. Trial 33 failed with context overflow (119.96s); tool-schema and nested-message representation are now budgeted. Trial 34 was cancelled after unsupported source-plan assumptions; it did not include the new filename tree. Trial 35 tests that tree with the unchanged read-only objective, Qwen3.5:4b, and no external GPT feedback. These are not acceptance successes.

Native fast follow-up: 100 context/core/memory/model tests passed in 65.36s; after retaining the prior unverified draft for targeted correction, 67 context/core tests passed in 37.50s. Trial 35 remained waiting_review after 145.87s; incorrect text-only worker assumptions were not accepted. IAB UI on isolated port18985 verified fast/APC selector separation, localized count summary, 310 cached files and zero changed/deleted/skipped after refresh. Found refresh summary did not update until reopening; refresh now waits for queued completion before rendering the new overview. Production not restarted.

IAB refresh correction verified: clicking Refresh updates the timestamp in the open map (17:24:50 to 17:25:49), retaining 310 cached files, without closing/reopening the dialog.

Full regression: 416 passed in 116.16s, before the final source-contract prompt refinement. Trial36: waiting_review,151.60s; worker input assumptions remained unsupported. This is a model reasoning failure, not an index coverage success. Subsequent prompts require the requested inputs to come from the user objective and require a source-grounded transformation for additional component inputs. No Ember files edited, no GPT feedback used, no 7B model loaded.

Trial37: waiting_review125.36s; trial38: waiting_review145.64s. Neither establishes semantic acceptance. Trial39 diagnostic used the same Engine/Qwen3.5:4b with thinking enabled and8192 output budget; cancelled after194.19s of repeated discovery, settings restored by finally. It did not establish a reasoning-mode benefit. Focused continuation fix subsequently passed67 tests in38.03s. An intermediate missing parenthesis was caught by tests, corrected, and the failing run stopped; passing result is the corrected run. Trial40 exercises the focused source-tool continuation without external feedback or diagnostic thinking override.

Final focused-continuation regression:416 passed in151.28s. Trial40 remained waiting_review after126.68s. Independent inspection also found wrong T2I quality value and missing required request fields; the local reviewer itself made an incorrect claim about prompt validation, so its critique is not independent truth. Trial41 is a diagnostic of thinking mode plus focused continuation, not a production setting change. No publication or production restart.

Trial41 diagnostic cancelled after251.58s of repeated equivalent discovery queries; no accepted plan. Temporary thinking/output settings restored, and Qwen3.5:4b unloaded afterward; Ollama reported no loaded models. Awaiting user preference on a short7B comparison versus retaining4B-only. Native index/mapping fixtures and UI checks are passing, but model semantic acceptance and release remain incomplete.

2026-11-07 user-authorized single7B comparison (trial42): actual Engine, Qwen2.5-Coder7B Q4_K_M, same objective/index/context32768/output2048, no GPT. Completed in80.98s, waiting_review,14 actions,9 distinct source files read. Independent review FAILED: the runner did not inspect existing image_video.py/image_video_worker.py/gateway.py before claiming there was no video-generation API; plan remained generic. This comparison does not establish a benefit from model size alone. Original audit settings restored; model unloaded immediately in finally; Ollama loaded_models=[] verified. Evidence: E:/AI/audits/ember-fast-20261107/acceptance-42.json and coder-comparison-independent-review.json. No Ember changes or production deployment.

### 2026-11-07 — component-first navigation
- Confirmed Ollama had no loaded models before implementation. Added a generic regression rejecting invented paths, deduplicating component selections and tracing every selected component. Focused context suite: 36 passed in 38.07s.
- Real local-only 4B task a11a81c1739640728119d870ad32c200 is being evaluated separately; no acceptance claim from fixture success.

- Additional source-contract fixtures: 3 passed in 0.07s, including conditional validators whose fields appear optional. Source snippets are retained without executing project code. Trial 43 ended waiting_review after 181.32s; independent inspection found incorrect image source_id usage and unsupported installation/queue claims despite improved component discovery. Not accepted.

- Full regression run before the final conditional-validator fixture: 419 passed in 115.84s. Trial 44: waiting_review, 176.14s; independently rejected for wrong image identifier and unverified model/worker recommendations. Evidence: component-investigation-review.json in the isolated audit folder. Trial 45 exercises the final validator-inclusive packets, with automatic model unloading in finally.

- Latest context/schema suite: 40 passed in 15.35s. Includes shared-dispatch schema evidence and fast database isolation. This is fixture/API validation, not a live public MCP or UI acceptance test.

- Trial 45 (a37bce1da1274cf9bfe0aafd3721dec4): independently rejected after the draft replaced text-only input with a user-supplied image and claimed operational success without execution. Diagnostic cancellation requested to avoid further redundant inference. Static evidence improvements do not establish semantic parity. No production deployment or completed-release claim.

- Trial 45 ended waiting_review after 158.83s; unload verified zero loaded models. Observed late source-review state overwriting cancellation; added a persisted pause/cancel check after review before state transitions. This control fix has targeted regression coverage; a real cancellation retest has not yet been run. Semantic source-understanding acceptance remains failed.

- Final engine core regression suite: 34 passed in 24.70s, including pause/cancel during the final source-review attempt. These tests do not upgrade the failed real source-understanding result.

2026-11-07 feedback continuity: context/engine suite 72 passed in 40.98s; bridge/protocol/guidance suite 46 passed in 9.85s. These are fixtures, not live acceptance. Live IAB ChatGPT sent a new read-only Ember source-contract request, but the listener initially remained idle with request_cursor_missing=true. Added confirmed outbound-ID fallback and restarted only isolated API18984 after verifying no queued/running/verifying tasks. Actual intake/result/review remains under observation.

2026-11-07 live feedback probe: public MCP accepted read-only tasks cf2d8531dcd74aabb8d1f9d3eca11e40, a28d203dbd914a268f92b1a3f11df593, cc6b64e1245249aa8ea3a217bf8e67e1 and b32affdc1ab14c539d90ab32f1ee5301. Real run_shell source evidence returned, and subsequent director correction produced another source read. However the local answer still misidentified consumed_epoch and later answered without a new tool action: semantic acceptance FAILED. Separate probe eb53df46ddfc4ac19c0d499222217432 repeated source reads and was cancelled by the test supervisor. This is not completion of the feedback feature. Public API8876 returned 404 for chat project binding; its runtime remains older than current source. Isolated PLAY18984 restarted (launcher3280) with the continuity fixes but reported waiting for page/login/verification; user asked to identify the visible state. No production upgrade or Git publication. All probe tasks inactive and Ollama models empty after cleanup. Evidence: E:/AI/audits/play-ui-20261107/feedback-mcp-probe-20261107.json.

2026-11-07 PLAY load-error repair: 50 bridge/protocol tests passed in 9.54s, including bounded retries and protection for drafts, pending sends, login, generation, overlays and changed URLs. Isolated API18984 restarted (launcher13208) after confirming no active tasks. Live IAB connection panel instead reported “Open the saved ChatGPT conversation or explicitly select a different tab”; clicking existing-tab selection did not restore the binding. Thus error-page recovery is fixture-tested, not live-verified. Production untouched.

## 2026-11-07 — PLAY original-chat recovery and two-way feedback (0.14.1)

- Automated fixtures: `python -m pytest tests/test_chatgpt_bridge.py tests/test_bridge_transcript.py tests/test_play_protocol.py -q`: **64 passed in 13.14s**. Includes saved bindings, missing/redirected tabs, per-chat cursors, stop/resume, new-chat bootstrap, pending-send preservation and busy inference notification behavior.
- Actual agent acceptance in isolated app 18984, Qwen3.5:4b, Web PLAY: first task `3ed1fa1597e94af694ae74686b4f828e` used project_context and read_file for pyproject.toml only; ChatGPT reviewed its tool evidence and independently issued the second step. Task `ac8fbbe954674f908bb4cea066fef81b` used project_context and read_file for hub/__init__.py only. Both reported 0.14.0 (the source version at test time), no tool errors or writes. ChatGPT's final review confirmed step separation and matching versions. Local task state remained waiting_review; this was not human approval.
- Original local/remote chat association was retained through service restart. Actual UI stop/resume retained chat_id, run_id, seen messages, action IDs, latest/own user IDs and outbound receipt, returned to listening, and did not send a duplicate bootstrap.
- Prior Recovery-02 was a failed scope trial: the model read both files on each step. It is not counted as acceptance; its observed failure led to separating CURRENT STEP from OVERALL HUMAN OBJECTIVE in dispatch.
- Evidence: `E:/AI/audits/play-ui-20261107/recovery-feedback-acceptance.json`, `recovery-continuity-before-restart.json`, `recovery-continuity-after-restart.json`, `recovery-ui-resume-proof.json`, and `recovery-feedback-success.jpg` in the same directory. Private runtime/chat data is not published.
- Limits: no OS reboot, no public MCP deployment/acceptance, no full Ember project understanding acceptance, and no universal browser/model guarantee. Native Hub implementation; no additional APC source copied.


## Recovery implementation resumed — 2026-11-07

User authorized execution of LOCAL_MODEL_RECOVERY_PLAN. Verified pre-edit snapshot: E:/AI/audits/recovery-baseline-20261107-185806 (247 files, ZIP bytes checked against SHA-256 manifest). Preserved pre-existing dirty work.

First native Hub correction: directed tasks no longer have repeated context calls silently replaced by autonomous exploration. Model events now retain done/done_reason and fingerprint/count metadata for prepared packets without storing another source-text copy. No APC source added.

Focused regression: 95 passed in 50.41s before the additional packet-fingerprint telemetry. Real isolated Engine task 99ff41c3914e433e8e5f6fea1b9e50bd took 37.95s and is NOT semantically accepted: it read both target files but ignored requested ranges and incorrectly generalized missing video capabilities from image-only excerpts. All four inference responses ended with done_reason=stop, so this observed failure was not output-length truncation. Prompt counts ranged from 7908 to 9478; prepared-packet telemetry was added after this run and is not claimed as its evidence.

Next: controlled exact-source mini-evaluation, then structured source/range obligations in the existing Guidance and shared dispatch. UI/MCP/PLAY acceptance and publication remain pending. No production restart or deployment performed.
# Recovery continuation — 7 November 2026

- Real GPT review of the worker draft was received in the existing feedback conversation and saved locally as `recovery-directed-20261107/gpt-worker-review.txt`. It rejects the unsupported `ConditioningItem(None)` proposal and distinguishes the observed worker from unverified pipeline capabilities. Codex manually relayed this diagnostic; it is not proof of automatic PLAY recovery.
- Directed prompt separation: 45 context/integration tests passed (18.57s). Real task `3a8f013be34545da929f31dcdd06990d` returned in 26.27s but still incorrectly inferred text-only capability. **Not accepted.**
- Minimal source-only adapter diagnostic: three 4B requests with the same numbered source and no tool catalog, saved in `minimal-worker-probe.json`. All ended with `stop`, not length truncation. Responses contain incorrect or contradictory branch interpretations; this is evidence of a reasoning problem even with a small packet, not a successful benchmark.
- Structured required-read real task `5c13804b287d46c79a2652ef195719be` executed the exact requested worker range. Coverage initially rejected its trailing empty line; that verifier bug was fixed and regression-tested. No semantic success claimed.
- Guidance/context/core checks: 83 passed (41.90s). Bridge/protocol/guidance after fixing a missing test import: 64 passed (13.54s). Trailing-empty-line/protocol checks: 10 passed (1.67s). An earlier run had 1 failure and 136 passes due to that missing import; retained, not counted as a passing run.
- No production restart, deployment, Git publication or Ember source modification is established by these tests. Autonomous and automatic-feedback acceptance gates remain open.

Recovery follow-up evidence (2026-11-07):
- Combined core/context/integration/guidance/bridge/protocol suite: **144 passed in 78.75s**. Per-call inference profile test: **1 passed**, 35 deselected (0.63s). These checks do not certify model understanding.
- Real structured source task `808b829c9c3a4ff3aa786769dbfaccaa`: 27.61s, exact requested worker range after AGENTS bootstrap, no further source exploration. Actual GPT critique was supplied. It corrected the mandatory-image conclusion, but line citations and an unsupported final proposal remain wrong. **Partial improvement, not semantic acceptance.**
- Identical small-packet thinking trial with 1600 output tokens returned no final answer and `done_reason=length` after 30.92s. A separate 4096-token diagnostic returned the correct core answer and matching line citations in 37.69s (`stop`), and a first repeat in 56.66s; the third returned in 46.80s with the correct branch/input conclusion. Its frame-extraction citation names the conditional start (45), not the exact call line (48), so exact citation acceptance is still imperfect. This is one controlled source question, not full runner acceptance; thinking is not enabled globally. The new per-call profile does not mutate persisted model preferences.

- After truncation guard: all 37 core tests passed (26.53s). The corrected coverage checker reports no missing source for task `808b829c9c3a4ff3aa786769dbfaccaa`; its semantic state remains waiting_review.

### Source coordinate recovery checkpoint — 2026-11-07
Read-only synthesis now sends explicit observed line numbers; raw action evidence stays unchanged. When formatting alone would evict the final source range, packet budgeting removes the added line numbers before discarding source. Native Hub change; no new APC code imported.
Validation: initial context-mode suite 1 failed/40 passed exposed the formatting overhead; corrected fallback then 41 passed in 16.08s. Model-context/source-contract/project-context tests: 27 passed in 3.09s. git diff --check passed (CRLF warnings only). No deployment or publication.
Second source diagnostic uses actual indexed image_video.py:31–47, hash 2fdab992e08a6fbf9c99221fcc607a960fb5a378c7a0a9a44c5b06489c01934f. Independent isolated Pydantic oracle tested all 12 kind/identifier combinations, with only three accepted. This is adapter diagnostic evidence, not runner acceptance. Thinking 4096 failed the first two repeats with empty final output and length exhaustion (80.89s/77.06s); third repeat still running at this checkpoint. Do not enable this as a global production default based on earlier worker-only successes.
User added optional GPT-to-local English instruction normalization. Preserve original request and derived instruction in durable provenance; only active-context inclusion expires. Existing context system instructions and translation-catalog default are English; source is not translated. Current failing diagnostic already uses English, so language normalization alone is not proven to resolve reasoning failures. Compare equivalent English/Hebrew requests before choosing policy. Use existing Guidance/PLAY pathways rather than a parallel task service.

Recovery source-contract diagnostic completed — 2026-11-07: all runs were English and without GPT/Git. Thinking4096: two empty length-limited answers, third 57.77s with correct field declaration list but incorrect treatment of project_id and incomplete prompt-only reasoning. Nonthinking4096 three repeats (6.76/7.16/5.72s) falsely made default fields required. Adding measured AST metadata fixed the field list but three repeats still inverted the validator semantics. A decomposed twelve-row truth-table prompt scored [5, 9, 10] out of12, against isolated Pydantic execution. Thus neither global thinking nor English-only rewriting is accepted as the solution. Artifacts: recovery-directed-20261107/contract-*.json; all failures preserved. Model unloaded; no running diagnostic remains. Next: source-bound GPT instruction/correction on this same contract, and autonomous verification/adapter comparison; do not claim automatic feedback or runner acceptance from these diagnostics. Optional translation must use existing Guidance provenance, retaining original input and derived instruction rather than deleting audit history. No new APC imports or deployment.

## 2026-11-07 — independent GPT correction and scoped runner

- Actual GPT browser feedback on the 17-line Generate contract corrected the local model. Three adapter trials matched all 12 independent Pydantic cases (9.55/4.81/4.80 seconds); no expected-case table was supplied to the local model. These are diagnostics, not runner acceptance.
- First Engine trial violated its prose read-only instruction by writing analysis_result.json. Stopped and rejected; preserved the exact hash-verified newly created file in the private audit and removed it from Ember by moving it. No prior-file backup existed.
- After tool-scope enforcement, Engine task 4b1ee9908527462d91f94b6231eeaa2c matched 12/12 cases in 21.34 seconds with only permitted reads. Still waiting_review; JSON format was not obeyed and automatic GPT return/review remains unverified.
- 68 guidance/bridge/PLAY tests passed in 13.93s. Earlier test failures (missing async test plugin and outdated protocol-version assertion) were corrected before this run. No production restart, commit or deployment.

## 2026-11-07 — external director evidence delivery

- Focused autonomous Engine trial b56a2bfe3bcc42888f367bacf7bc33d1 completed in 106.58s as waiting_review/unverified. Three drafts each scored 12/12 against the saved independent Pydantic oracle; all added prose rather than returning only the requested JSON. The first prose misquoted the boolean expression. Local reviewer later rejected correct case rows with self-contradictory explanations, causing unnecessary revisions. This separates successful case extraction from failed format/review completion. No GPT, Git, media jobs, code edits or downloads were used by this task. Actual logs and table-only scoring saved privately. Next change must address unsupported local-review contradictions rather than repeat the same case-generation trial. The whole objective remains incomplete.

- Autonomous recovery diagnostic: measured finite predicate cases enabled Qwen3.5:4b to return 12/12 correct validator combinations in 9.78s, without GPT or an answer table supplied by a director. Expected values were compared with the previously recorded independent Pydantic oracle. This is an adapter result, not whole-project understanding. Runner task 398a6db6e689444da57cadbf37924a6c broadened into 11 source ranges and exhausted output after 90.56s. Exact-path trials 1f73b744e5d246baa46a8d5dc4731b5a and c8055da7aa5e422e876632cf2f068098 exposed oversized derived metadata in the source compactor. Fixed metadata priority and complete-class extraction. Trial 8435b458b274449d99a64c1ef584746d still used general context and entered repeated local review; cancellation requested after two rejected drafts. Added focused autonomous synthesis preserving the exact question and measured source facts. No success inferred from these failed trials; artifacts retained privately. 26 focused source/model-context checks passed in 0.21s and four navigation/synthesis checks passed in 0.61s. No new APC imports, deployment or publication.

- Live public MCP source-review trial: first request incorrectly replaced an absolute source path with sandbox/exploration.py. Director correction restored the exact path, but subsequent broadening caused truncation and unnecessary reads. A five-line extraction then succeeded with one tool action in about seven seconds. The local model's interpretation contradicted itself (initial yes versus later no). Independent director correction through the same MCP chat produced the correct false/None interpretation in 2.16s with zero tools. Four terminal waiting_review tasks and full recorded actions/events are preserved privately in live-mcp-source-correction.json. This proves one live same-chat MCP correction cycle, not autonomous semantic correctness, same-task revision guidance, Web PLAY, or activation of development code. No application code was changed by those MCP tasks.
- Directed paged-source synthesis: three focused tests passed in 0.64s. The regression verifies two chunks from the required SHA256 are combined and an older complete version cannot fill a gap. New behavior is native Hub; APC unchanged.

- Follow-up source-retention fix: 66 bridge/source-feedback/visual-recovery tests passed in 12.58s, including a fixture that corrects an answer without new reads and excludes an obsolete screenshot. Replayed the stored real Engine revision 84: old attempt filter returned zero sources; full history contained 21 unique excerpts, of which seven were delivered and 14 explicitly omitted by the bounded packet. Packet total including metadata/omission manifest: 29,215 UTF-8 bytes. No new inference or external delivery occurred in this replay. Public MCP inventory responded but did not contain the isolated acceptance task; this does not establish deployment. No additional APC reuse.

83 focused source-feedback/guidance/bridge/transcript/PLAY tests passed in 15.71s. Replaying actual Engine action evidence produced two complete source excerpts in 3,439 UTF-8 bytes, including image_video.py 31–47. This verifies packet construction, not public connector deployment. Internal-browser GPT review was requested against the real runner draft and this packet; acceptance of the full automatic loop remains pending.

- Independent GPT review in the existing IAB conversation returned semantic_verdict=supported and format_verdict=needs_correction. Exact response and screenshot were saved in the private audit. This was a Codex-relayed diagnostic, not an automatic PLAY/MCP acceptance. Next action: feed its format correction back into the same runner task via revision-fenced review and verify the resulting JSON, then exercise transport delivery and held-out project scenarios.

- Source-review continuation fix: a source-only director task may return a corrected draft using its recorded source evidence without being forced to execute a fresh action. It remains waiting_review, never semantically approved. This fixes the observed waiting_user result after three redundant synthesis attempts in revision 79. Required-source coverage and other execution-task completion checks remain enforced. Validation: 79 context/core tests passed in 43.56s before this continuation fix; 3 targeted director tests passed in 1.80s afterward. Automatic external feedback transport and autonomous semantic acceptance remain outstanding.

- Actual Engine follow-up revision 84: 21.27s, waiting_review, corrected producer existence/result lookup and prompt-embedding/image-conditioning contradictions. No new source actions were required; same-task existing evidence was reused. This is a directed correction with supplied expected cases, not held-out autonomous reasoning acceptance. Returned actual draft to the existing IAB ChatGPT conversation for independent review; first transmission was incomplete and detected as unavailable, then the complete payload was submitted after verifying composer contents. No duplicate executor task was submitted. Qwen unloaded after testing.

- Independent IAB ChatGPT review of actual revision84 returned supported_with_minor_limitations, 7/7 bounded semantic cases. Minor caveats: distinguish submission endpoint from generation service, explicitly retain unknown underlying image-free model support, and represent consistency separately. Review saved privately as gpt-correction-verdict.json/png. This manually relayed, answer-guided diagnostic does not prove automatic PLAY/MCP operation, generalization, deployment or whole-project autonomous understanding. No active test process remains; Qwen unloaded.


Unreleased — 2026-11-07: local source-review rejections now require exact draft and observed-source quotations before automatic rewriting. Ungrounded criticism preserves the candidate answer in waiting_review with an explicit unverified label and audit event instead of repeating synthesis. Quotation matching does not prove semantic correctness. Native Hub implementation; no APC source reused. Five focused review/control tests passed in 4.79s; live acceptance recorded separately.

Focused source answers with measured input contracts now honor an explicit human request to return a JSON array using the existing model adapter schema option in an answer-only stage. This constrains syntax, not semantic correctness; ordinary requests retain source navigation tools. One focused fixture passed in 0.60s. The preceding unconstrained actual run b359a7d434c3478fbf9079b5194416b0 reached the output limit after 38.38s and is not a pass.

Actual autonomous Engine acceptance 87ef5ae966cc4845ab1b3e7960db4d20: 18.28s, Qwen3.5:4b, no GPT/Git. Complete JSON array, 12/12 unique cases matched the saved independent Pydantic oracle after verifying the current source SHA-256. One local review returned an unsubstantiated rejection; no rewrite loop occurred, draft retained in waiting_review. This verifies the narrow extraction/format/no-loop behavior, NOT general project understanding or external review/deployment. Ollama /api/ps empty after unloading the test model; both stores had zero active tasks. Private evidence: E:/AI/audits/recovery-directed-20261107/grounded-review-score.json.


Unreleased — 2026-11-07: source reviewers may select exact inclusive source line anchors instead of reproducing code. The runtime resolves the quotation only inside delivered source ranges and still requires an exact draft quotation; range coverage does not prove semantic correctness. This avoids losing legitimate criticism because a small model mangles code or newline escaping. One focused review fixture passed (0.61s). Native Hub change, no APC code reused. Broad autonomous trial 6a2be3068e5643b193148bebf04af7b2 failed in 61.27s despite 15 observed source ranges: unsupported model-capability claims and a new backend instead of composing existing producers/consumers. Its local critic identified a real non-image branch error but provided a nonmatching quote. The trial remains a failure, not indexing acceptance.


Unreleased — 2026-11-07: broad source synthesis ranks task-matching implementation ranges ahead of incidental recent reads. Filename overlap is only a retrieval hint; measured contract/flow presence breaks ties. Budget trimming now drops the already-used filename map and duplicate derived contracts before dropping raw source. Source logs retain all ranges. Replaying failed task 6a2be3068e5643b193148bebf04af7b2 previously delivered only text_image.py, text-image.html/js and config.py (11 omitted); the corrected packet retains text_image.py, image_video.py and image_video_worker.py, preserving the producer/consumer/validator sources. This packet replay is not semantic acceptance. Two focused fixtures passed (0.62s). Native Hub changes, no APC source copied.

2026-11-07 follow-up: broad autonomous 225fdd4c5c674af0aaa162d78de8100f took 137.8s and remained semantically incorrect after local review. With source prioritization, 08dfbeb2d76d4461975bf6bdcfc140bf took 35.55s and correctly proposed composing existing producers/consumers, but still misread fields, asynchronous readiness and runtime availability. Neither is acceptance. A manually relayed IAB ChatGPT correction resumed the same task (revision14) in18.44s: core input/readiness understanding improved, but invented underscore routes, a fixed timeout and cleanup behavior remain. Next method separates director-owned synthesis from bounded executor fact extraction; no repeated broad self-review. The revised Engine recorded delivered source manifests in this real run. No Ember changes, deployment or new APC reuse.

Unreleased — 2026-11-07: the shared MCP/PLAY director contract now changes responsibility after a failed semantic correction: director owns synthesis and decisions; executor returns bounded source facts before concrete implementation steps. It explicitly checks route declarations, async readiness, field mapping and evidence for cleanup/retention. This is guidance, not a guarantee that the provider follows it or proof of automatic transport. One focused PLAY protocol test passed (0.23s). Native Hub change, no additional APC source reused.

2026-11-07 same-task revision24: the bounded director fact-extraction step completed in25.14s but FAILED semantic and JSON acceptance. It fixed route prefixes, yet again confused required/defaulted fields, omitted request_id, emitted a Python conditional inside JSON, and misstated some worker/cancel paths. Do not repeat another broad or compact local interpretation of the same source. Next supervised implementation must deliver exact runner-owned source evidence to the director without rewriting it through Qwen; the director then provides concrete execution steps. Existing source_feedback already retains raw text and hashes and is used by both bridge_controller and mcp_gateway; extend that shared path instead of creating a parallel index or transport. Autonomous broad reasoning remains unaccepted. Engine manifests prove revision14 delivered all6 requested ranges; source preservation alone is not semantic correctness. Actual audit files remain under recovery-directed-20261107. No active/queued tasks in QA or production stores at cleanup; Qwen4B unloaded. Public MCP inventory still exposes the older seven-tool surface and no Ember project, so new code is not verified deployed. No services restarted, no commit/push, no additional APC reuse, no Ember changes.

### 2026-11-07 — original source feedback
- 20 focused tests passed in 2.47 s (source feedback, guidance, PLAY protocol).
- Real isolated Engine resumed task 08dfbeb2d76d4461975bf6bdcfc140bf, revision 33, in 2.30 s and returned six requested Ember Video ranges, waiting_review. No model-start events occurred in that guidance epoch.
- After repairing hash extraction from fast references, replayed its recorded source actions and independently compared all six texts and full-file SHA256 against disk: all matched. Ollama /api/ps was empty. Evidence: E:/AI/audits/recovery-directed-20261107/original-source-verification.json. Hash fix replay is not a second runner run.
- Not established: automatic GPT receipt/review, production schema availability, autonomous semantic correctness, full recovery-plan acceptance.

### 2026-11-07 — PLAY source handoff
- 55 existing bridge tests passed in 12.26 s. New regression validates current-only verbatim evidence once, no historical source duplication, and transition to waiting_reply (1 passed in 0.72 s). It initially exposed a KeyError for missing optional total_lines; repaired the compactor, with 16 model-context tests passing in 0.13 s.
- Internal Codex browser successfully reopened the original signed-in feedback conversation. No new diagnostic message sent this segment; browser availability is not proof of automatic feedback execution.

### 2026-11-07 — schema completeness
- 11 source-contract tests passed in 0.17 s, including syntactically valid truncated classes. Actual persisted Ember fast index: text_image.py1–23 is partial; class16–24 is complete and recovers project_id. Evidence: recovery-directed-20261107/schema-completeness-verification.json. This is adapter evidence, not autonomous semantic acceptance.
- Live MCP inventory was rechecked: only seven legacy tools and old sandbox projects are exposed. Latest guidance/exact-patch transport is not currently accessible there. User asked to restart normally because earlier automatic QA restart was policy-rejected. No restart attempted.


### 2026-11-07 — source packet budget correction
- Autonomous runner task `05ded7ec507f46949144771e75834804`: 103.31 seconds, waiting_review; failed semantic acceptance (inferred automatic orchestration from a UI link). Qwen unloaded afterward, Ollama models empty.
- Context suite initially 46 passed / 1 failed: omitted-location hints evicted the final source. Fixed source priority; four targeted budgeting/directed-source tests then passed in 2.32 seconds. This is fixture evidence, not semantic acceptance.
- Live local OpenAPI after user restart exposes GuidanceRequest.evidence_only; public health responds 0.14.1. Connector tool inventory still has only seven tools, so full updated MCP guidance availability remains unverified.

- Task 77b9fbdd30b748ad88aa28661a542a7e terminal waiting_review in 75.06 seconds. Semantic acceptance FAILED: ignored the composition of existing text-to-image and image-to-video and instead proposed unverified image-free dependency behavior. Review also produced unsupported judgments. No further unchanged trial is justified. Need preserve the relevant producer/consumer evidence together and verify independent director control. Session 57993 terminal; Qwen unload requested after termination.

- After the final source/hint priority fix, the complete context-mode suite passed: 47 tests in 17.15 seconds. This supersedes the earlier 46/1 fixture result, not the failed autonomous semantic trial.

- Map audit on Ember Video: 310 eligible files, 310 indexed, all hashes match, complete paginated coverage; 214 valid Python files / 1689 AST symbols matched. install_qwen.py has a pre-existing unterminated string at line 15, remains text-searchable. Other languages have text indexing, not full symbol graphs. Coverage regression: 1 passed in 1.07s. Audit: recovery-directed-20261107/map-coverage-audit.json.
- GPT reviewed actual original source attachment in the existing feedback chat and requested four additional ranges. Same Engine task 08dfbeb2d76d4461975bf6bdcfc140bf revision 40 retrieved all four in 3.86s with evidence_only, no local inference. All returned texts and full hashes matched current files. This was manual relay and is NOT autonomous PLAY/MCP acceptance. Follow-up packet still needs returning to director.
- User clarified map/retrieval is distinct from semantic feature planning. In supervised mode GPT owns file selection and judgments from the beginning; local model implements scoped prose tasks, exact patches use deterministic tools. Autonomous mapping diagnostic d0153d74eda2427198c8c8dd62c76f0e session42780 started before newest coverage metadata edit; do not claim it validates that edit.

### 2026-11-07: Keep read-only mapping within the requested scope

The real autonomous runner task d0153d74eda2427198c8c8dd62c76f0e ended after 129.47 seconds with an unverified draft that proposed integration work despite a mapping-only objective. Shared source instructions incorrectly required change/test planning for every read-only investigation and a capability-contract table for every synthesis. These requirements are now conditional on the actual request; mapping asks for measured coverage, navigation and relationships. No APC code was imported for this fix. The first regression run found a source-budget regression (47 passed, 1 failed); synthesis instructions were shortened instead of weakening the evidence-budget assertion. Task 76966f004c074a3394f3c62207e39c3f is an actual runner diagnostic launched before that final prompt shortening; its outcome is pending. This is not production or semantic acceptance.

### 2026-11-07: Preserve measured index coverage in synthesis

Actual runner task 76966f004c074a3394f3c62207e39c3f returned an unverified draft after 84.59 seconds. It incorrectly called the 310-file index filenames-only and confused omitted packet entries with parser coverage. The synthesis packet discarded overview.coverage; it now carries measured_index (mode, total_files, coverage) separately from the bounded filename tree. This is a native shared Hub fix, not imported APC code. Qwen was unloaded after the trial.

The four exact follow-up ranges from task 08dfbeb2d76d4461975bf6bdcfc140bf revision40 were manually uploaded to the same GPT conversation. GPT read them and returned corrected source-cited defaults, image readiness, video polling and terminal/recovery states; it requested no additional ranges for that architectural proposal. It explicitly excluded runtime and automatic PLAY acceptance. This validates manual director review of raw runner evidence only, not unattended transport or independent local reasoning. Screenshot remains in the private audit directory.
`nCoverage propagation regression: first run had 48 passed/1 fixture error (missing source ref); corrected the fixture to the actual tool schema. Full context modes suite: 49 passed in 16.82s. Actual runner c2e4b6a3c96e463aa71ebb271200b4fb is running with the shortened synthesis instructions and coverage propagation; session11995. No semantic pass claimed.

### 2026-11-07: MCP catalog diagnostic

Importing the current gateway in the isolated QA root and calling its list_tools returned 68 tools, including project_index, project_context, context_search/expand/related, task_guide and task_request_changes. The currently connected MellowCodex connector exposes only seven legacy tools. Its saved chat/project inventory was read successfully. This is a verified catalog discrepancy, not proof of its cause (cached connector schema versus a different/older running gateway remains unresolved). Do not claim supervised MCP acceptance from local registration. Active autonomous task c2e4b6a3c96e463aa71ebb271200b4fb remains under observation via session11995.

### 2026-11-07: Preserve rejected drafts and diagnose gateway catalog

After three local source-review rejections, Engine previously saved its retry placeholder instead of the latest executor answer. This deprived task_answer and external feedback of the actual draft. Engine now retains that draft, records source_review_exhausted with the critic result and verified=false, and returns both under waiting_review. It does not turn critic rejection into success. Engine regression: 1 passed (39 deselected), 1.16s.

Gateway health now reports a fingerprint/count of its public tool input schemas and whether the source-guidance tool set is registered. No project contents, paths, tokens or credentials are exposed. This helps distinguish the loaded gateway catalog from a cached connector catalog. Six remote tests passed in 2.21s after correcting the SDK field name input_schema. This change is not yet loaded in production. No APC code was reused for these fixes.

Actual autonomous task c2e4b6a3c96e463aa71ebb271200b4fb ended waiting_review after 154.19s; semantic acceptance failed. The final critic questioned image/video conditioning but this alone does not establish a source contradiction. Qwen was unloaded after the run. No unchanged rerun was started.

### 2026-11-07: Exact director patch execution
113 focused Engine, guidance, bridge and PLAY protocol tests passed in 47.40s. After adding parser, replay and uncertain-action checks, 15 guidance tests passed in 3.13s. Two Engine fixtures use the real ToolRunner and candidate storage: valid exact code is written unchanged and diff returned; a stale hash leaves the file unchanged and is not retried. Both prohibit model calls and leave the original workspace untouched. These are controlled fixtures, not live GPT/MCP/PLAY acceptance. The initial trial exposed an unnecessary project_context bootstrap; it was removed for exact patch steps. Earlier full core/task_answer regression result: 52 passed in 30.85s. No model was loaded for these tests.

### 2026-11-07: Mapping review scope and latest real trial
Local review now receives measured_index coverage and is told to evaluate the user's actual mapping/navigation request rather than automatically turning it into feature feasibility analysis. One focused regression passed (48 deselected, 0.62s). This is native Hub code, no APC reuse.
Real autonomous Engine run e5ff40b10c0b4d719b78f8142a41f0ac took 91.99s, ending waiting_review, not accepted. It reported the measured 310 files/1689 symbols correctly, but focused on video, omitted requested image/voice coverage, invented hyphenated Python filenames and produced an unsubstantiated local critique. Trace shows 17 read ranges but only 3 delivered in the final synthesis packet. Initial model queries lumped all requested subsystems together and selected panel/gateway/requirements instead of their implementations. This identifies navigation coverage plus packet allocation as the next concrete fault; another unchanged full run is not justified. Qwen was unloaded; api/ps returned models:[].
Runtime check after user reopened the UI: desktop PID 23804 is not elevated; existing Hub/gateway PIDs 5932/18692/18672/5320 are still elevated. Active HTTP GuidanceRequest still lacks exact_patch; gateway health still lacks tool_catalog. The UI restart did not reload these services. Do not claim deployment or connector refresh.

### Full shutdown — implementation verification
- `python -m pytest tests/test_shutdown.py -q`: 2 passed in 0.41s. Fixtures verify ordered stopping/unload/desktop/server exit, idempotent concurrent requests, and unload failure preventing exit. No real services were stopped by these tests. Live desktop, public MCP and actual VRAM release remain unverified.

- Administrator shutdown launcher: desktop shortcut created and its target verified. Read-only `scripts/shutdown_agent.py --inspect` found eight installation/owned service processes; executed=false. Actual elevated shutdown deliberately left for the user who requested to open it. No claim of verified runtime shutdown.

### Director onboarding packet (in progress)
Added project_brief shared by HTTP, local tools and MCP: measured map, original hashed opening sources and optional task search; no local inference or Git dependency. Native Hub addition; no new APC source imported. Two focused tests passed in 1.30s. Real ToolRunner packet 2696eaec7bfa44c08a62b99df46878aa returned 310 files / 1689 Python symbols, and three opening-source ranges verified against disk hashes and lines. This is adapter evidence; fresh GPT review and live transport acceptance remain pending.

### Fresh director conversation evidence
GPT in new conversation 6aef7bc6-2348-83ed-9872-a7389d4c9b7a read the actual project_brief attachment and correctly identified the standalone studio and measured parser limits. It requested four source ranges. Actual isolated Engine task 6ba47bcda6dd46f3b49c48f03236a8f4 returned them in 1.42s without model inference; task remained waiting_review. One source was omitted by the bounded feedback packet. Added task_source (HTTP/MCP) to retrieve an observed source action without rereading/rerunning and preserved total_lines. All four source hashes and requested line texts checked against disk, returned to GPT for review. Six source-feedback tests passed in 0.07s. Transport here is manual relay; unattended PLAY/MCP remains unproven. No new APC code reused.

- 2026-11-07: targeted atomic source-request API regression: 1 passed (20 deselected).
  Fresh GPT chat 6aef7bc6-2348-83ed-9872-a7389d4c9b7a reviewed the recorded Engine
  sources and correctly separated declarations from unproven orchestration;
  requested a second bounded range set. This was manual relay, not PLAY automation.

- Live production Engine source retrieval 735b886f11ed4f62a8ae1cbb650e091d: waiting_review in 3.22s. Real public MCP get_task delivered evidence. All eight recorded source ranges matched original files and SHA-256; three omitted ranges retrieved from live HTTP source route. New-tool public discovery and automated PLAY remain unverified.

### Mapping-only acceptance continuation
- Fresh GPT chat directly called existing MCP project_context, context_search and
  context_expand (reported six calls in 26s) and returned source-grounded paths/ranges.
  UI response observed; a server-side receipt was not yet enabled for those calls.
- Added context_access receipts for future direct HTTP and runner reads.
- Added bounded context_read guidance/PLAY envelope; existing Engine executes it
  without inference. Real isolated map task 5f2e61dbec38410b91c82c4b6259b301 completed
  to waiting_review in 0.76s, with project_brief action and 310 source-policy files.
- Focused context_read/brief regression: 3 passed, 15 deselected. Earlier guidance/
  protocol regression: 16 passed. No live automated PLAY claim.


### 2026-11-07 PLAY objective conversation continuity
Live mapping acceptance exposed that starting a bounded objective created a second local chat for an already linked GPT conversation. Sending failed at the ownership check before composer submission. Start now reuses the linked local chat, rejects cross-project reuse, and includes the current PLAY protocol. Focused fixture covers same-chat continuation and project isolation; live acceptance still pending. No Ember Video services or media execution are required for indexing.

Live PLAY GPT requested context_read brief with a wider read-tool allowlist. Guidance now intersects that list with the single selected tool; explicit exclusion still rejects. Two focused tests passed. A rejected pre-dispatch guidance step now becomes failed rather than leaving a queued orphan. Initial live attempt executed no tools; acceptance continues after reload.

2026-11-07 live PLAY loop completed in linked chat e249a777ce6d46bbb6a28bf2820991b1: GPT requested brief, related metadata, then four hashed source ranges; local runner returned results automatically and GPT produced a source-backed map. Tasks 973b29dbce5942679acfac676933a125, 06dd978fe882467fb6c70b4f33510aa5, 6a75df94c60249af9765dbb7ffefc5a8. No local inference or project mutation requested. Evidence: play-map-runner-evidence.json and play-map-director-final.txt in the recovery audit directory (not committed). First two steps also recorded an unnecessary scope-rejected project_context bootstrap; deterministic context_read now skips that bootstrap. This final cleanup still awaits normal deployment. MCP direct retrieval was observed earlier; full release/publication remains pending.


### 2026-11-07 direct MCP mapping acceptance
In the connected GPT conversation, three actual MCP calls completed: project_context, context_search (project storage/versioning), context_expand (ember_video/projects.py lines 120-206). Server context_access receipts confirm all three HTTP-backed calls; GPT described save/revision/current/history behavior and explicitly separated source verification from runtime execution. No Git access, media execution or local inference was requested. Receipt evidence is stored outside the repository at E:/AI/audits/recovery-directed-20261107/mcp-map-access-receipts.json. PLAY separately completed brief -> related -> exact source -> director review automatically. All five returned PLAY source hashes independently match current files. New convenience MCP wrappers may remain absent from existing client catalogs; the existing direct context tools were the tested route. Publication and the final bootstrap cleanup deployment remain pending.

Final deterministic context bootstrap cleanup deployed by normal shutdown/start. Three focused context_read tests passed in 0.77s. PLAY completed at review_ready before shutdown; after restart its bounded run is stopped, with the linked conversation preserved. Ollama reports zero loaded models. Full goal remains active pending coherent versioned Git publication and final completion audit.

2026-11-07 shared director contract clarification: 19 protocol/guidance fixture tests passed in 2.88s. These checks do not constitute a new live transport test or universal enforcement of all generic actions. Existing live map/source acceptance remains the evidence for the bounded deterministic path.

2026-11-07 release check: 68 focused context-mode, project-brief, source-feedback and source-contract fixtures passed in 17.80s. Current production UI displayed 310 indexed/unchanged files, fast mode, and successfully searched `save projects.py` and expanded its original save/revision code. This was read-only UI verification, not an Ember runtime test. git diff --check passed.

### 2026-11-07 SelfDevelop development verification
- Five focused tests passed (session persistence, retry identity, review gate, unscoped execution rejection, MCP correspondence, no-progress regression).
- Actual Engine/ToolRunner in isolated state read this repository through project_brief in 0.734 seconds and returned waiting_review; no model inference was needed. Evidence: E:/AI/audits/selfdevelop-acceptance-20261107/result.json. This was a locally supplied director instruction, not a live ChatGPT/MCP conversation.
- JavaScript syntax checked. Additional provider authentication, complete self-restart/rollback and deployment are not validated by these tests.

- Reloaded idle Hub/MCP services. Live routes returned HTTP 200 and all four SelfDevelop tools registered. In Codex IAB, opened AI connections and Claude MCP setup: shared endpoint, OAuth instructions and unverified-provider notice rendered correctly. No provider login was performed.

## OmniRoute research validation — 2026-11-07

- Verified 72 unique provider IDs after excluding authentication-method entries; preserved exact upstream LICENSE bytes and recorded SHA-256 for nine reviewed source files.
- An initial exact-license assertion detected differing file bytes; replaced the local notice with the upstream bytes and reran successfully.
- Source inspection only: no provider connection, multi-agent execution, PLAY adapter or production acceptance test performed for this research step. No services restarted or models loaded.

## 2026-11-07 — delegation development verification
- Five focused delegation/SelfDevelop tests passed (2.46s). Covers durable state, stale revision rejection, review gates, mock parallel workers/dependencies and credential-safe errors.
- Actual Ollama 0.5B API worker returned a proposal; unloaded immediately. Existing local Engine ran project_brief and stopped at waiting_review with a recorded completed tool action. This fixture had no populated index; it proves routing/execution, not correct project mapping. The director was the test harness, not live GPT. Proposal quality was imperfect and was narrowed by director instructions; no claim of autonomous comprehension.
- IAB at isolated port 18983 verified provider card rendering, editing and saving a director name. Registered MCP adapter functions then read that UI-saved profile and saved another profile through authenticated test HTTP. This is adapter integration, not public ChatGPT end-to-end acceptance.
- Reported parser toast traced to missing BridgeController in the lifespan-disabled QA launcher; corrected launcher returned HTTP 200 for chatgpt/status. Node fixture confirmed HTTP 500 plain text gives a readable error without its raw body, and normal JSON still works. app.js/delegation.js syntax checks passed.
- Screenshot: E:/AI/audits/delegation-acceptance-20261107/provider-cards.png. Runtime fixture evidence remains outside Git. Production activation, public MCP/PLAY director acceptance, interrupted-dispatch recovery and complete multi-provider orchestration remain pending.


## APC/SelfDevelop audit — 2026-11-07

Source-only audit: all 24 selected APC files matched pinned hashes. Real ChatGPT MCP task efda4497e65d44d3a278f29e268a4714 failed before any action (local model manually unloaded; free-form inspect submission). Gateway refresh changed its live catalog from 78 to 86 tools; the same ChatGPT chat still reported 68. Client discovery and candidate repair remain in progress. No full self-activation acceptance.

## SelfDevelop pause checkpoint — 2026-11-07

Real ChatGPT/MCP created candidate `4d9dda844bfb477b921375cef1714ce9`; revision 4 is saved, not deployed. Candidate tests: revision 1, 52 passed/1 failed (20.27s); revision 4, 8 passed/1 failed (4.70s). Failures use outdated MCP call signatures lacking a valid chat_id; these are not passing suites. The malformed-guidance and baseline-path regressions passed, but review gaps and full activation acceptance remain. See [handoff](docs/SELFDEVELOP_HANDOFF-2026-11-07.md). At pause: no queued/running/verifying tasks, no loaded Ollama models; temporary test server stopped. No new tests were run for this documentation checkpoint.


## Unreleased — 2026-11-08: SelfDevelop exact commands

Added selfdevelop_command (MCP) and POST /api/selfdevelop/{chat_id}/command. The director supplies one explicit command, shell and timeout in an existing SelfDevelop chat. The local task runner executes it without local-model rewriting, records the action/output, and waits for director review. Reused request IDs return the original task; conflicting content is rejected. Pending/failed commands are not automatically replayed. Guidance is validated before new task creation; unresolved SelfDevelop turns block orphan followups. Same-task request_changes accepts waiting_user while preserving revision and uncertain-action guards.

Validation: recovery/guidance suite 28 passed at isolated candidate revision 1; six exact-command tests passed at revision 4, including real PowerShell execution through Engine with model calls forbidden. After user-authorized one-time bootstrap and service restart, live task 90fb9378e5214734963d433f8465048a executed one run_shell and returned SELFDEVELOP_LIVE_EXACT_COMMAND_OK; evidence was inspected through MCP. The new command was submitted via the authenticated local API because this chat cached the earlier MCP tool list. A fresh MCP tool-list/session is needed to expose selfdevelop_command to this client.

Limitations: this is not full autonomous SelfDevelop acceptance. Automatic control-plane deployment, rollback/restart recovery and corrected-command retry remain incomplete. Image transfer and Desktop shortcut repair remain pending. Preserve the current worktree and review changes before Git publication.


## Unreleased — 2026-11-08: correction of exact commands

Added selfdevelop_command_correct and POST /api/selfdevelop/{chat_id}/command/correct. A director can submit a corrected command for the current waiting_user/waiting_review task with an exact task revision, stable correction ID and reason. Original goal and previous actions remain intact. Atomic event/queue update records prior action IDs so only the new command runs; uncertain pending effects and stale revisions are rejected. Timeout accepts 1..180 seconds to match the existing executor.

Validation: candidate revision 5 passed all eight command tests, including real Engine/PowerShell failure (exit 7), same-task correction, successful new output, no model calls, idempotency and pending-action rejection. The live agent installed the four changed files using base-hash checks and backups under E:/AI/audits/selfdevelop-correction-v5. Read-back hashes matched the candidate. Automatic scheduling of restart was rejected by approval review with blocked by policy; no retry or bypass was attempted. Live correction acceptance awaits user restart. Full autonomous self-upgrade/recovery remains incomplete.


## Unreleased — 2026-11-08: reject syntactically broken self-updates

Corrected a malformed app.py route introduced in revision5. The earlier eight command tests did not import app.py and were insufficient evidence of server startup; the failed deployment was rolled back with user approval. Exact candidate patches now reject malformed Python before publishing a revision; candidate test certification parses every Python source, including modules outside selected tests. Candidate revision6 passed 39 tests including app import, actual command execution/correction, and syntax gate regressions. Agent installs eight reviewed files after all-source parse and hash checks, with backups. Live correction route awaits normal service restart; full control-plane automatic deployment/rollback is still incomplete. Desktop English Start and Stop All Services links were created/read back through agent actions; shutdown was not executed by the director.


## SelfDevelop control-plane revision12 — 2026-11-08

The local task runner applied exact director patches in an isolated candidate. Earlier real-process runs failed: Windows venv process identity differed from the launcher and psutil reported bound listening sockets as NONE. Corrections retain exact workspace/module identity, recognize the configured runtime, and require HTTP health from the newly launched process family.

- Candidate revision12: tests/test_control_plane_processes.py and tests/test_control_plane_update.py: 10 passed in 13.87s. Two tests launch real isolated FastAPI service pairs on temporary ports: successful source update and intentional import failure followed by restoration of old source/services. These are isolated process tests, not a production restart.
- tests/test_development_api.py, tests/test_selfdevelop_commands.py, tests/test_selfdevelop_recovery.py: 18 passed in 7.13s.
- Local agent installation task e134b565de9b45bfb81cffcbeebc4c15: exact hashes and Python AST checked before seven file replacements; backup and readback completed; restart_performed=false.
- Failed-run leftover isolated processes were stopped through the local runner; no remaining targeted processes. Production Hub returned HTTP200.
- Pending: actual production activation, MCP reconnection/status retrieval, external discovery of new tools, autonomous-model self-development, and real requested-image transfer. None is claimed completed by these checks.


2026-11-08 candidate revision13: tests/test_worker_guidance_packet.py and tests/test_coding_worker.py: 6 passed in 3.34s. Covers compact payload, changed guidance rejection, source scope, unchanged response and syntax correction. No real inference tested. One historical packet inspected was 54,376 bytes total and 5,139 guidance bytes; this does not prove guidance size caused its failure.


2026-11-08 Mellow Guard naming: local runner appended and read back the requested service name in README, CHANGELOG and VALIDATION. No behavior change or additional runtime test; production activation remains pending.


## Real Mellow Guard update ? 2026-11-08

Local task e67da81a7a6f4cb0aab3558c83dea4ff applied isolated candidate 44084fdcb7734d9e8fd74e251cde8f62 revision2. Nine status/recovery tests passed in 2.03s. The old negative restart-capability assertion was updated for the new supported behavior; local runner task 779b2c24c71e4d8f818813598a067bda ran that updated file: 2 passed in 0.83s. No claim that the original negative assertion passed.

Product control-plane prepare/activate endpoints staged and launched update 2e6b8031b2ad4e509da4a1e70c80749d. Its independent supervisor PID20444 exited with durable ACTIVE_VERIFIED. A fresh authenticated status request confirmed that state. A subsequent call through the external MellowCodex MCP connector returned supervisor=Mellow Guard and control_plane_restart_supported=true in the same linked chat. This verifies real Hub/MCP source activation and reconnection. Activation used the product HTTP endpoint because this chat's discovered tool catalog still lacks the new wrappers. All-service/desktop restart, dependencies, real production failure rollback, standalone autonomous model development and requested image handoff remain unverified.


### SelfDevelop review safeguards ? 2026-11-08 (Unreleased)
A real Qwen Coder 7B trial fixed timeout validation but removed existing shell/command guards despite passing 15 scoped tests. Director review rejected that patch. A subsequent model correction returned unchanged source. The coding-worker instruction now explicitly preserves existing guards and requires reviewing unintended deletions; a targeted regression covers invalid shells, blank commands and oversized commands. These are risk reductions, not a guarantee of model correctness or proof of autonomous self-development. The final correction is director-authored and agent-applied in a candidate; production activation remains pending. Candidate regression: 22 tests passed in 10.13 seconds, including preservation of all three command guards.


Unreleased 2026-11-08: coding-worker packets now include the latest exact-command correction reason and request identity, without executable command payloads, while retaining the original objective. Previously the exact-command correction was recorded but omitted from the worker packet. A focused transport regression verifies latest-reason delivery; real-model correction acceptance remains pending.

## 2026-11-08: SelfDevelop failed-step director closure (isolated candidate)

- A director may explicitly close a terminal failed step after reviewing evidence, requiring owning chat, exact task revision, nonblank reason and stable request ID. The operation atomically enters the existing cancelled state, records an audit event, retains the original goal/result/history and never replays actions.
- Stale revisions, wrong chats, pending uncertain actions, active states and repeated closures with conflicting request IDs are rejected. Synthetic acceptance creates a failed step, explicitly closes it and completes a new step within that same chat.
- Candidate 0878dd3533db4547a22cacd2eea9910b revision 8: 30 focused tests passed in 9.97 seconds; verified true, source_changed []. Further edits require retesting the final revision.
- Refresh tools in ChatGPT resolved missing Mellow Guard prepare/activate/status and exact command tools. This new candidate is not yet deployed; supervised recovery does not constitute autonomous software development.
# Service recovery 0.15.3 — 2026-11-10

Real installed scheduled task executed successfully with LastTaskResult 0 and five loopback services reachable. Controlled interruption of the manually launched gateway (exact captured process IDs/command lines) recovered through the scheduled task. Real MCP model_memory_status succeeded afterward with qwen3.5:4b loaded and inference enabled. Repeated scheduled execution retained replacement launcher/child pair, avoiding duplicate launches. Broker readback: Running, Automatic after native approval. No reboot, locked-session, foreign-listener or hung-process termination test; no broad synthetic suite. Existing legacy Hub was not restarted. Git publication remains pending due to concurrent workspace changes.


Unreleased — 2026-11-10: Added desktop MCP Start/Stop/Restart/Status controls with serialized durable manual stop and exact process ownership. Recovery checks SSH reachability, reports IPv4 Duplicate conflict, preserves relay restart budget while unreachable, and checks post-launch survival. Real Stop/Start restored local services; remote acceptance blocked by Ethernet static IPv4 collision. See docs/MCP-SERVICE-CONTROL.md. No reboot acceptance claimed.


2026-11-10 follow-up: Owner approved Ethernet DHCP after confirmed Duplicate static IPv4. Prior configuration backed up locally. New preferred DHCP lease acquired; next automatic scheduled run restored relay (LastTaskResult 0), and real remote MCP model_memory_status succeeded. Model was unloaded; no inference or full reboot test claimed. Installed Start/Stop/Restart/Status shortcuts; Stop/Start exercised. Changes remain Unreleased alongside unrelated concurrent work.

