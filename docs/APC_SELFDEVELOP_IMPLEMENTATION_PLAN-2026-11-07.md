# APC integration through supervised SelfDevelop

Status: implementation plan and source audit, not a claim of completed APC migration or autonomous self-update. Date: 2026-11-07. This extends the existing technical and local-model recovery plans; it does not replace the working index, browser, task runner, conversation store or Guardian.

## 1. Required outcome

A user selects a local project and asks a question or requests a change. The Hub supplies a compact measured map. GPT (or the configured director) requests relevant source ranges, evaluates them, issues one bounded instruction, and reviews the recorded result. The local executor reads, patches and tests exactly within that instruction. Git is optional. Repository content and previous model output remain evidence, not authorization.

For SelfDevelop, the target project is the Hub itself. Development happens in an isolated candidate. The director must inspect the actual diff and test evidence before approving a step or proposing activation. A response saying “done” is not proof. Restarting the process that carries the request must not lose the operation or cause it to execute twice.

The minimum acceptance is a real MCP conversation that reads Hub source, causes a candidate repair, receives a failing-then-passing regression and exact diff, requests a correction if necessary, and explicitly approves the observed candidate revision. Candidate acceptance and production activation are separate outcomes.

## 2. Source and reuse audit

APC means **AI Project Center**. Inspected source: `E:/AI/audits/apc-github-2026-11-07-da47822/apc-main`, commit `da4782284cff68e3310749583f6f0b26e0907d55`. All 24 source files recorded in `apc-reuse-manifest.json` matched their recorded SHA-256 during this audit. Evidence: `E:/AI/audits/apc-selfdevelop-review-20261107/source-audit.json`.

APC is a PHP application with its own browser bridge, operations, project maps and context subsystem. Its composer manifest declares a proprietary license. Retain user ownership and dependency notices. Do not relabel it as an MIT component. Its cognitive-continuity candidate documentation itself lists pending runtime/release/browser evidence; source existence is not proof that all APC behavior was accepted.

The Hub has **native Python implementations of selected APC contracts**, not the complete PHP runtime. Python AST/SQLite FTS5, the incremental queue, current task runner and CDP browser remain the foundation. File counts are not a meaningful percentage of migration. This audit copies no new APC executable code.

| APC source | Existing Hub behavior | Remaining useful integration |
|---|---|---|
| `inc/project_map.php`, `api/project-map-search.php` | `hub/context/service.py`, `indexing.py`, `fast.py`, `apc.py`: files, hashes, source ranges, Python symbols, FTS search, aliases/tags and relation candidates | Typed non-file entities and explainable graph expansion; broader language extraction with explicit coverage |
| `inc/project_map_components.php` | Native component/source investigation exists; not an equivalent APC port | DOM/component signatures and repeated-instance grouping. APC's selector normalization is UI grouping, not proof of code semantics |
| `inc/project_map_living_manual_v2.php` | Durable file annotations survive rebuilds | Canonical feature identity; audited rename/merge/split/exclude/representative corrections; separate observations from human/director interpretation |
| `inc/context/obligation_compiler.php`, `task_contract.php` | Task objective, scope, source requirements and review contracts exist | Explicit obligation ledger: objective, target, constraints, acceptance, current state, source scope, execution path, verification, completion |
| `budget_optimizer.php`, `candidate_engine.php`, `context_router.php` | Bounded brief/search/expand and source delivery receipts | Coverage-aware selection over multiple detail levels; mandatory evidence cannot disappear because another hit scores higher |
| `session_delta_planner.php` | Chat identity, source hashes, persisted history and retrieval receipts | BOOT/DELTA packets scoped by conversation, task epoch and source version; delivery is not acknowledgement |
| `recall_classifier.php`, `reminder_engine.php`, `capability_cues.php`, `token_metrics.php` | Searchable conversation anchors and optional memory review | Task-specific reminders and measured packet costs; targeted capability cues instead of injecting the entire catalog |
| `inc/verified_capabilities.php` | Action log, errors, test results, candidate revisions | Verified solution lineage, preconditions and invalidation. A past workaround is a candidate, not a universally safe instruction |
| `project_source_history.php`, `project_map_backup.php`, `project_connection.php` | Candidate snapshots, hash checks, explicit workspace authority | Document provenance and complete activation/recovery transaction; do not create a second snapshot engine |
| `direct_chat.php`, selected `ops.php`, `workstreams.php` contracts | Persistent conversations, stable request IDs, task revisions, PLAY/MCP feedback | Close interrupted submission/review/reconnect gaps; do not import the entire APC queue or authentication layer |
| APC browser runtime diagnostics | Existing `hub/browser.py`, CDP/Playwright and `remote_input` | Selectively add before/after capture, console/network/overflow evidence and tab budgets through existing adapters |

Historical “remaining” fields in the original manifest describe earlier checkpoints. They are not current status: indexing queues and real supervised mapping have since been implemented. Current mapping evidence is in `MAPPING_ACCEPTANCE-2026-11-07.md`: 310 eligible Ember Video files matched 310 indexed files, with real MCP and PLAY source retrieval. That does not validate independent Qwen reasoning; the recorded 4B/7B semantic failures remain failures.

## 3. Immediate SelfDevelop prerequisites (P0)

### P0.1 Discover the deployed capability contract

Compare source catalog, running gateway catalog and actual client-exposed tools. On this audit the source had 86 tools, running gateway 78 and a new ChatGPT conversation reported 68. The older Codex connector exposed only seven tools. These observations are separate layers, not proof of a single cache cause.

The running gateway has been replaced by the existing Hub supervisor and now reports 86 tools. Verify client rediscovery separately. Expose build/catalog hashes and supported operations in a compact read-only capability result, also visible in the UI. If the requested structured operation is unavailable, report that exact prerequisite. Do not silently substitute a free-form model task.

Client rediscovery was subsequently verified in the same ChatGPT conversation after its existing plugin's **Refresh tools** action. GPT could call `selfdevelop_start`, `selfdevelop_step`, `selfdevelop_review` and `request_sources`. This was a catalog refresh, not a new permission grant.

### P0.2 Install guidance before enqueue

`SelfDevelop.step` currently submits a chat task before validating `Guidance.submit`. Invalid guidance can leave a queued orphan that blocks the next request. Fix globally: validate the complete payload before creating executable work, and make the remaining creation/guidance transition recoverable. Preserve rejected-attempt evidence; never delete an already executed task or report cancellation as success. Validate request-ID replay against the complete normalized payload. A reused ID with changed sources, patch, scope or operation must conflict.

Apply the same invariant to source-request and other pre-dispatch callers. A crash between task creation and guidance attachment must recover as “awaiting guidance” or a recorded rejected attempt, never run unrestricted. Enqueue is the final operation. Review retries must be idempotent and revision checked.

### P0.3 Deterministic executor path

Use existing `request_sources`, `context_read` and exact-patch paths. These operations must work with Ollama manually unloaded. Do not ask Qwen to translate or rewrite an exact GPT patch. Local inference is optional for a bounded coding subtask; its proposal still undergoes the same hash checks, diff and director review.

The real trial exposed a mode-specific contract defect: `request_sources` supplies indexed relative paths, but baseline `ProjectContext.row` accepts only opaque `id:hash` references. `FastContext.row` already accepts paths. Repair this in shared source resolution without changing the project's selected index mode, weakening current-hash validation, or reading unindexed/private paths. Exercise both expansion and related-file lookup. Until repaired, direct candidate reads are an explicit bounded fallback, not evidence that `request_sources` succeeded.

If the director needs arbitrary implementation, request a candidate snapshot, read original files with hashes, propose exact changes, run one relevant regression, then inspect the diff. No live-repository edit is implied by candidate creation. Returned source excerpts are complete only for their stated ranges.

### P0.4 Reliable activation and recovery

Current Guardian supports **patch-worker releases only**, and `SelfDevelop.status` explicitly reports no control-plane restart support. Do not advertise it as a complete self-updater.

Extend the existing Guardian with an external supervisor process; do not place the controller solely inside the Hub process being replaced. Persist an activation journal outside release directories with release ID, source manifest hash, prior release pointer, intended services, phase and health observations. Enforce one activation lease and reject new deployment while mutations have uncertain effects. Stage a complete immutable release with matching Hub/gateway code; validate dependencies and DB compatibility before stopping services.

Activation phases: prepared → draining → stopped → switching → starting → health-check → committed, or rollback → recovered/failed. Restart only verified owned processes. Wait for HTTP and MCP protocol health, matching release/catalog hashes, database readability and one harmless runner request. On failure restore the previous pointer and start the previous release. Persist the terminal result so reconnection can retrieve it. A missing connection does not establish a successful shutdown or update.

Keep schema changes additive and backward compatible for the first release. Backup/restore must not overwrite legitimate writes made after the backup. Dependency, launcher and DB migrations require an explicit release contract; they are not ordinary exact file patches. Preserve approved launch elevation without disabling UAC or fabricating privileges.

Acceptance: candidate edit/review first; then a disposable isolated Hub+gateway update/recovery test through MCP; finally one authorized production activation with reconnect and unchanged chat identity. Do not force a production failure just to demonstrate rollback.

## 4. APC integration stages after P0

### P1 — Typed graph and corrected project manual

Extend the existing context database through versioned migrations. Proposed records: `entities(id, project_id, kind, identity_key, source_hash, extractor_version, payload)`, `relations(from_id, to_id, kind, evidence_ref, certainty)`, `annotations(entity_id, revision, operation, before, after, author, reason, evidence_ref)`. Names are proposed, not currently installed tables.

Use kinds file/symbol/route/page/selector/component/feature. Never interpret a route or selector as a filesystem path. Keep measured imports/calls/locations distinct from heuristic relationships and director-reviewed meaning. Source-change invalidation must follow evidence dependencies; manual corrections remain in the overlay and become stale when their supporting evidence changes.

Use existing project registration, inventory, hashes and update queue. Fast/native and APC-enriched modes select one analysis policy over the same inventory, without double watchers or competing indexes. Preserve raw paths and source language. English internal field names do not require translating file contents, literal search terms or user constraints.

One useful acceptance: a local fixture with a route, template and symbol, plus an unrelated similarly named file; retrieve the measured relationship, label ambiguity, change one source and invalidate only dependent observations. Then repeat one real project question through GPT/MCP, without Git.

### P2 — Obligations and bounded context packets

Represent each obligation with stable ID, original text, kind, hard/soft flag, scope, provenance and supersession. Retain the original request verbatim alongside director-normalized English execution steps. Do not rely on the same small model to repair its own misunderstood translation.

Candidate context items have source hash, exact range, detail level, estimated cost, observed token count when available, covered obligation IDs and confidence. Choose a compact map plus evidence covering hard obligations first; then fill remaining budget with novelty/utility. Return `missing_obligations` explicitly. The director asks for missing sources instead of guessing or receiving every file.

Store complete history locally, but state the distinction: durable history can grow with disk capacity; the model's active context remains finite. Summaries and RAG do not magically produce an unlimited inference window. A source expansion must still be available from every summary.

### P3 — Conservative continuity and deltas

Implement BOOT on a new conversation, provider switch, task-epoch change or reset. DELTA is allowed only for matching project/task/conversation/source versions and acknowledged context. Store packet ID, evidence manifest, sent state, acknowledged state and consumer epoch. A sent message is never automatically acknowledged.

For providers without explicit acknowledgement or stable reference handles, default to compact resend of mandatory context. For providers that support them, send hashes/references for unchanged acknowledged material and actual content for changed/new obligations. Git URLs are optional source locators; a private inaccessible or changed Git revision cannot replace a verified local source range.

Acceptance: reconnect with the same identity, new chat, changed source, missing acknowledgement and provider switch. Each should produce the correct packet policy with no cross-project context assumptions.

### P4 — Verified repair memory and capability cues

Record failed attempt → observed error → changed approach → diff → test evidence → director verdict, keyed by problem class and preconditions. Store exact environment/source revisions. Retrieval suggests prior solutions; execution rechecks relevant preconditions and current authorization. Invalidate a solution when new evidence contradicts it. Keep speculative advice separate from verified outcomes.

Use task-specific capability cues drawn from the actual deployed catalog. Context tools do not need a local model. Browser/OCR and code tools are selected by task need, not loaded as one enormous prompt. Prefer the existing action log and conversation store over a parallel memory database.

### P5 — Selective browser evidence

Reuse APC's diagnostic contracts only where missing: before/after targeted screenshot, URL/tab identity, visible modal state, console/network failure and overflow checks. Extend `hub/browser.py`/`remote_input`; do not import APC's whole server, SSH/auth stack or a second browser session controller. Respect the user's physical mouse and existing app capture limitations. A locked Windows desktop is not equivalent to an interactive desktop; DOM/CDP and file operations may continue, but unsupported captures must report their limitation.

## 5. MCP director work protocol

1. Read deployed capabilities. Create/reuse a SelfDevelop session with explicit objective and stable external conversation key.
2. Request a compact project brief through the actual runner; review recorded evidence. If the client lacks the structured tool, refresh discovery or report the prerequisite.
3. Request exact source paths/ranges/hashes. Keep the same local chat; each bounded step has a stable request ID.
4. Create an isolated candidate from current source, including authorized uncommitted work. Read the candidate revision and file hashes.
5. Director proposes the smallest patch. Executor checks scope, candidate revision and base hashes, applies exact content, and returns the diff. No local-model paraphrase of code.
6. Run a focused test relevant to the changed behavior. A test command succeeding is not enough: return collected test outcome and exact candidate revision. Reject a stale review after another patch.
7. Director approves that revision or requests a specific correction. Failed or uncertain actions require reconciliation before retry; no new request ID to replay an uncertain write.
8. Prepare a release only after candidate acceptance. Invoke the external activation controller when available; poll its persisted operation across disconnects. Otherwise report candidate accepted, activation unavailable.

Tool availability is checked at runtime. Future table/packet/activation APIs described here are **planned**, not callable instructions. Use existing `candidate_*`, `get_task`, `task_source`, `task_guide` and review tools only when discovered. MCP is request/response; the director must poll and issue follow-ups. Web PLAY may automate its exchange, but uses the same scope, evidence and review contracts.

## 6. Performance and verification discipline

Machine budget: 32 GB RAM, RTX 3050 8 GB VRAM. Base scanning/hashing/AST/FTS use no model. Coalesce filesystem events and incremental updates; Git events trigger inventory comparison, not repeated full semantic inference. Avoid two heavy models in memory. Exact source/patch execution does not load any model. If a small-model proposal is necessary, record the chosen model and unload after the test when it was loaded for that test.

Use one focused regression per actual defect and one practical director/executor round-trip per new boundary. Do not rerun a large suite after documentation changes. Keep failed evidence and state why the next approach differs. Stop repeated successful reads that produce no new evidence or progress; return to the director with the missing decision, not a fabricated completion.

Every APC-derived implementation must add source path, pinned commit/hash, destination, direct-copy/contract-reimplementation classification, deviations and actual validation to the manifest. Every capability must state whether it is source-only, locally exercised, available on the running gateway, visible to the client, or accepted through the real agent.

## 7. Current acceptance log

- Source provenance: 24/24 pinned manifest hashes verified.
- Existing mapping: previously recorded real MCP/PLAY evidence retained; not rerun or upgraded to autonomous-model success here.
- First fresh GPT/MCP trial: task `efda4497e65d44d3a278f29e268a4714` failed before any action because GPT used a free-form inspect task while the local model was manually unloaded. No candidate or fix resulted. This is retained as a failure.
- The same GPT conversation initially could not discover `request_sources` or `selfdevelop_*`. The running gateway was refreshed from 78 to 86 tools; client rediscovery then succeeded after refreshing the installed plugin's catalog.
- Real MCP SelfDevelop session `d7fff46dc0814785b3343f8c88f37d45`: task `eaa5c6738db94eeb80dedc06585d29e9` executed `project_brief` through the task runner and reached director-reviewed `done`, revision 6. Ollama remained unloaded. Evidence: `E:/AI/audits/apc-selfdevelop-review-20261107/selfdevelop-brief-run.json`.
- Source task `d8e3499e01a844899c286adb71074b0b` failed with three `context_expand` errors in APC baseline mode. Evidence: `E:/AI/audits/apc-selfdevelop-review-20261107/source-request-failure.json`. GPT created candidate `4d9dda844bfb477b921375cef1714ce9` via MCP and is repairing the contract from inspected source. Candidate creation alone is not repair acceptance.
- Full Hub/gateway self-activation and recovery remain unimplemented at this checkpoint. Do not mark the overall SelfDevelop objective complete from a unit test or candidate-only result.

## 8. Pause checkpoint

Work paused at the user's request before computer shutdown. ChatGPT used MCP to prepare candidate `4d9dda844bfb477b921375cef1714ce9`, revision 4; it remains isolated. Test runs: revision 1, 52 passed/1 failed; revision 4, 8 passed/1 failed. MCP fixture signature failures and review gaps remain. Full activation is not implemented. The earlier in-progress entry is superseded by [the exact handoff](SELFDEVELOP_HANDOFF-2026-11-07.md). No new tests were launched for the pause.
