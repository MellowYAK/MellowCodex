# Supervised SelfDevelop completion plan — 2026-11-08

**Scope:** GPT is the sole director through MCP. The local agent executes bounded instructions, runs tests, maintains durable evidence and reports state. No autonomous/local director implementation or research is authorized. This is a technical planning document, not a release, deployment, or semantic acceptance.

## 0.17.1 current supervised handoff (2026-11-08)

- **Exact required scope:** GPT directs via MCP and the local executor performs EXACT bounded commands and returns source/action/Guard evidence. No local model planner or autonomous/local director is in the current acceptance target. This is the explicitly authorized guided track.
- **Confirmed patch:** candidate 4c9e771fa50c4320b46160fcb02dc821 rev1, task ffb03fbbf0ea4e9a837ff86ae539ea2e done rev6; receipt test-019636fd46fe4805ab0a2e9207165119.json: 19 passed in 30.58 seconds, verified=true, source_changed=[]. B approved just two paths, hub/development/selfdevelop.py and tests/test_objective_authorization_idempotency.py; they implement idempotent unchanged authorization replay after task done, not new authority to execute.
- **Verified Guard identity:** update af565cd45e71443e999b04fd2565aac4 is ACTIVE_VERIFIED. Two installed source hashes match the journal and candidate rev1. This is installation of the exact correction, not proof that a separate optional planner experiment succeeded.
- **Failed/limited optional experiment:** selfdevelop_run_objective in local chat 0f8ac1936e52470ea41ab86a8d60f689 hit context budget BEFORE writing and remains reconcile_required. This is NOT success and not permission to retry without reconciliation; no local model planner is requested.
- **Original supervised completion:** Guided exact MCP completion VERIFIED in original chat 8cae5657612a4fbeb390c51a8201fb64: correspondence.messages message_id=83fb81753a474ca38cf77d0417d248d2 (dedupe suffix chatgpt-final-verified-guided-idempotency-install-20261108-001). Root verified the persisted report via MCP get_chat. Guard update af565cd45e71443e999b04fd2565aac4 ACTIVE_VERIFIED; MCP reconnected; 2/2 installed SHA-256 hashes match candidate and journal; receipt test-019636fd46fe4805ab0a2e9207165119.json 19 passed in 30.58s, verified=true, source_changed=[]. Installation task c976f61108eb4270b0b286451392aa18 done revision 6, exit 0; Qwen loaded=false, models=[]. This is a guided GPT-director exact-local-executor success, NOT success of the separate automatic selfdevelop_run_objective experiment (chat 0f8ac1936e52470ea41ab86a8d60f689, context budget exceeded before write, reconcile_required); MCP reconnect did not itself wake ChatGPT.
- **Roles:** A handles source/candidate/Guard supervised execution; B reviews exact evidence; C publishes only already approved bytes plus metadata and documentation to existing PR #1. No merge, reset, live source write or restart by C.

## Evidence boundary

- Live repository: `E:\AI\repos\local-agent-hub`; targeted read-only inspection of `AGENTS.md`, SelfDevelop, service, engine, MCP, Guard and conversation storage. No full-project scan.
- Development candidate 35531dae6d224810827c8a0f01e63f47 rev26 bootstrap was read-only approved by B; receipt test-c9fb1b11e8e84465a1c792cf028a6905.json shows 17 passed in 11.54s, verified=true and source_changed=[]. A separately owns live proof of full Objective Driver; it is still pending.
- Historical rev22 journal interruption regression and rev23 partial semantic-review / rollback-reporting blockers were fixed by the bootstrap rev26. Guard update 6e9420b617cf40a19d35e4187256ace9 has ACTIVE_VERIFIED and eight exact installed hashes matching rev26. This does NOT prove a live full objective or same-chat completion.
- `AGENTS.md` requires truthful release/validation history, evidence from the local runner, no credentials or runtime secrets, and publication distinct from deployment. This document makes no code/version changes.

## Component and proven gap map

| Component | File(s), live / candidate | Existing evidence | Precise gap or pending verification |
|---|---|---|---|
| Human objective, scope and durable phase | `hub/development/selfdevelop.py` (live lines 18–90; candidate snapshot lines 37–187) | Live persists a chat-scoped objective and requires director tool scope; candidate adds `selfdevelop_objective_runs`, `objective_status`, bounded authorization and compare-and-swap phase progression. | Full lifecycle is candidate-only pending A's fix, B's independent verification and installation. Do not infer general autonomy from persisted phases. |
| Repair and exact test receipt | `hub/development/service.py` (live lines 110–172, 174–235); `hub/development/worker.py`, `hub/development/runner.py` | Authorized paths/tests, snapshot hashes/revision, syntax preflight, bounded local model repair and actual pytest receipts; focused worker edits and per-test Python bytecode isolation already exist. | `verified` is test execution success, **not** semantic director approval. Need exact candidate revision, unchanged source and recorded receipt for every accepted step. |
| Driver and review binding | Candidate hub/development/selfdevelop.py and hub/app.py review | B independently accepted rev26 exact review binding for bootstrap installation; installed SHA matched. | A separate live objective must prove that only an explicit GPT semantic decision binds the tested candidate revision and file fingerprint. |
| Engine lifecycle and guard | `hub/engine.py` (live lines 275–302, 494–502); `hub/development/selfdevelop.py` | Exact instructions execute locally without model rewriting; code tasks owned by SelfDevelop finish `waiting_review` even if verification checks pass. | Verify candidate's objective advances without erroneously bypassing `waiting_review` or running a second unapproved step; keep cancellation/failure boundaries. |
| MCP route / director transport | `hub/development/tools.py` (live lines 4–49), `hub/mcp_gateway.py` (live lines 315–342), `hub/app.py` (live lines 610–670) | MCP tools expose start/status/step/review and Guard prepare/status/activate. The system reports director=`external`, executor=`local`; transport `mcp`/`play` is a communication channel, not a director mode. | Check only exposed candidate endpoints and response/error contracts when A finishes. Generic MCP `INVALID_ARGUMENT` masking a SelfDevelop `Conflict` is a **secondary diagnostic issue**, not a release blocker or reason to weaken the guard. |
| Guard identity, interruption and rollback | hub/guardian/control_plane_jobs.py and hub/development/selfdevelop.py | Rev26 fixed unique Guard prepare journal reconciliation and accurate rollback watcher; installed ACTIVE_VERIFIED. | A must prove Guard ACTIVE_VERIFIED and approved-vs-installed hashes on a separate real objective; rollback is a reported failure, not success. |
| Same-chat correspondence and delivery boundary | hub/conversations.py, hub/development/selfdevelop.py, MCP gateway and tools | Rev26 supports idempotent original-chat verified/rollback report, accepted for bootstrap. | No live end-to-end original-chat completion report yet. MCP reconnect does not awaken an ended GPT conversation; the local worker cannot invent a callback. |

## P0 work by dependency and exclusive ownership

| Priority | Action / dependency | Exclusive owner | Required evidence for done |
|---|---|---|---|
| P0.1 | **Bootstrap fix complete:** A fixed rev23 failure-atomic GPT review binding and rollback watcher/report in candidate rev26; B approved; installed via Guard update 6e9420b617cf40a19d35e4187256ace9 with eight SHA matches. | **A - Manage Local Agent Development** | Receipt test-c9fb1b11e8e84465a1c792cf028a6905.json: 17 passed in 11.54s, verified=true, source_changed=[]; ACTIVE_VERIFIED. Bootstrap only, not full live acceptance. |
| P0.2 | **Bootstrap audit completed:** B accepted rev26 for installation, including two earlier P0 blockers. B continues independent read-only review of A separate real live objective proof. | **B - SelfDevelop Gap Review** | Bootstrap rev26 source evidence and exact Guard update verified; full live objective approval remains pending. |
| P0.3 | **PENDING live proof:** GPT-authorized objective -> bounded local repair/feedback -> exact GPT semantic review -> Guard active verified -> approved/install hash match -> same original-chat completion. A demonstrates, B reviews. | **A demonstrates; B independently reviews** | Full live success requires ACTIVE_VERIFIED, exact hashes and same-chat success report. Rollback/stop/reconcile only show safe failure. MCP cannot wake GPT after the conversation ends. |
| P0.4 | **Bootstrap publication authorized:** C adds only eight approved source/test files (with unrelated app delegation.js asset hunk excluded) and required 0.17.0 metadata/documentation to isolated release branch and PR #1. No merge or deployment. | **C - publication only** | Check exact Guard hashes, focused tests, staged scope/security, remote SHA and PR #1 open; A separately continues full live proof. |

## Definition of done / evidence contract

1. **Task authorization:** original human objective, GPT-chosen `allowed_tools`, paths/tests and stable request IDs are persisted; no executor widens scope. `waiting_review` is resolved before a new step.
2. **Candidate repair:** isolated changed-file hashes, candidate revision, actual failed-test feedback and subsequent test output recorded. `pytest passed` is only a test receipt.
3. **Semantic decision:** explicit GPT review must bind failure-atomically to exact tested candidate ID, revision, fingerprint and test evidence. A binding failure must not leave partial `done` / `review_decision` or an unusable retry. Stale review and cancellation stop.
4. **Guard:** unique journal matching and no interrupted-action replay; Guard activation after explicit GPT approval. **Successful live proof requires `ACTIVE_VERIFIED` plus installed-file hashes matching the reviewed candidate.** `ROLLED_BACK`, stopped or `reconcile_required` are safety outcomes and **failure to install**, not success.
5. **Delivery:** idempotent accurate report in the original local chat for both verified activation **and** rollback/stop/failure. **Successful proof requires the same-chat success report, `ACTIVE_VERIFIED` and installed hash match.** Reconnecting MCP does not wake a completed GPT conversation or confer a new GPT decision.
6. **Publication:** source PR updated by C after evidence approval, SHA verified at origin; publication is neither merge nor production rollout of the whole Git branch.

## Deferred / expressly excluded

- Autonomous/local director, automatic local semantic acceptance, auto-deploy from pytest, model selection policy expansion.
- New parallel orchestrator, second state store, alternate Guard, generic callback/wakeup into GPT, a permanently running conversation agent.
- Full-project rescans, wide test suites without an identified dependency, desktop/dependency upgrades, UI/delegation/wallpaper feature scope.
- Cosmetic MCP `Conflict` diagnostics are secondary and may be handled in a later separate fix; preserve safety blocking meanwhile.
- **No merge to `main`, no deployment from C, no code changes by B or C.** A alone changes candidate code; B audits; C maintains this plan and PR after approval.

## Current handoff

Candidate 35531dae6d224810827c8a0f01e63f47 rev26 bootstrap is B-approved and Guard update 6e9420b617cf40a19d35e4187256ace9 ACTIVE_VERIFIED; eight installed file hashes match candidate. C publishes this approved bootstrap to PR #1 only, while A continues the distinct live end-to-end proof and B reviews. Never report full success before same-chat completion proof. No local director or C-side deployment.
