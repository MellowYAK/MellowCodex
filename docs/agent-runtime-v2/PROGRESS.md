# MellowCodex Agent Runtime V2 — VERIFIED PROGRESS AND RESUME LOG

THIS IS THE SINGLE MOST IMPORTANT FILE FOR A NEW CHAT OR MODEL. Read MASTER_PLAN.md beside this file, then read this checkpoint and independently check live Git and system state. Do not depend on prior ChatGPT conversations, model memory or verbal claims.

## Current checkpoint (as last recorded)
Project status: IN PROGRESS, not production-complete.
Last session date: 2026-11-15.
Current milestone: P10 guidance candidate rev2 TESTED (105 passed, 5 legacy XFAIL) but NOT DEPLOYED; deployment and authorization blocked. P11-P14 and Engine integration remain open.
Last VERIFIED milestone: P01 durable master/progress VERIFIED DONE; P00/P02 audit and baseline VERIFIED PARTIAL.
Master document creation: task d18e4d376d9b44eb8a18f54895719b85, exit 0, 10,908 bytes, SHA256 AB994EC2E6D449F2390769A62A0C50BEEBF994C7F956362B04117F9BF120B161.
PROGRESS document: VERIFIED CREATED and independently read back (task 56f3cbe329424a06bf104811905fdcd9, exit 0).
Next action: Clear the terminal-failed normal task 073a1e73947a45e193ce4379d8e72011 through an authorized review/cleanup path (no replay), correct the stale SelfDevelop Guard-repair objective, restore authorized update pathway, verify P10 Guard deploy and live tests, then P11-P14/Engine integration. Before local Git push, reconcile origin/main changes with 15+ pre-existing dirty files safely.

## FINAL MEASURABLE GOAL
An autonomous, fast and safe MellowCodex agent runtime that turns a request into a durable versioned plan, executes browser/Windows/files/code/MCP actions with appropriately routed local/DeepSeek/optional cloud models, continuously checks tool feedback, accepts mid-run corrections, recovers and replans, and only claims completion after verified evidence. It must survive switching chats/models or process restarts without losing task progress or repeating uncertain side effects.
Full exact acceptance tests and implementation P00-P14 are in MASTER_PLAN.md. The following are NOT YET ACHIEVED release gates:
[ ] >=95% task success on versioned beta suite.
[ ] 0 false-completion decisions on blocking negative suite (Walla home is not Walla login).
[ ] 0 unauthorized R2/R3 actions or duplicate external effects under injected timeouts.
[ ] Browser 2-3-step task latency p50 under 6 seconds, p95 under 15 seconds across >=100 runs.
[ ] 0 LLM calls for verified deterministic action paths.
[ ] 100% pass of defined restart-resume and user-correction suites.
[ ] Evidence/decision trace for every action and approved model route.
[ ] Safely preserve SQLite content, credentials, Guard and user projects and prove rollback.

## Milestone status ledger
| ID | Name | Status | Evidence / blocker |
| --- | --- | --- | --- |
| P00 | Source audit, baseline and provenance | PARTIAL | Git branch/HEAD, dirty worktree, source presence counted; database/model/current service state and full test baseline still unknown. |
| P01 | Durable MASTER_PLAN and PROGRESS | VERIFIED DONE | Fresh readback task 56f3cbe329424a06bf104811905fdcd9 exit 0; MASTER_PLAN 10908 bytes SHA256 AB994EC2E6D449F2390769A62A0C50BEEBF994C7F956362B04117F9BF120B161; PROGRESS initial 9003 bytes SHA256 2A1E0779C7807DD94B350461E8F9DDE2B097C6ABAEC16CA29A55E6D19AB75AB7. |
| P02 | Acceptance fixtures and benchmarks | VERIFIED PARTIAL | 32 versioned synthetic scenarios deployed; live 46 passed, 1 skipped, 5 strict xfailed in 1.36s. Known wrong-host login and generic done-without-evidence gaps. Guard update 73fb7d73542c4672830052ea65a44aff ACTIVE_VERIFIED; 100-run real latency/E2E outstanding. |
| P03 | Typed TaskPlan/Step/Evidence contracts | VERIFIED DONE | New independent hub/agent_runtime_v2 contracts: immutable Pydantic TaskPlan/PlanStep/AcceptanceCriterion/Evidence/DecisionRecord/ActionRecord, DAG and freshness validation, stable semantic action key; Guard b3c51b57570646429d732e9dea506e7a ACTIVE_VERIFIED; live tests 62 passed 5 known P02 xfailed. Not yet wired to Engine. |
| P04 | Additive SQLite plan/event/checkpoint persistence | VERIFIED DONE | New agent_runtime_v2.persistence PlanRepository with explicit additive tables, plan history/CAS, evidence/event idempotency, crash-resumable checkpoints, legacy data preservation; Guard update 4d54969a56a14ded9161407b7f17da06 ACTIVE_VERIFIED; live 73 passed / 5 prior xfailed. NOT yet connected to Engine or production DB. |
| P05 | Universal adapter to existing Goal Board | VERIFIED DONE | New pure hub/agent_runtime_v2/goal_board_adapter.py converts existing editable BoardStore records to TaskPlan with original multilingual goal, revisions, alternatives and required final acceptance. Guard 3c792bc6a6164472990b74f68a090eb7 ACTIVE_VERIFIED; live 85 passed, five known P02 strict xfailed. Not yet connected to Engine. |
| P06 | Tool/browser/desktop/user feedback and evidence | VERIFIED DONE (standalone) | New feedback.py normalizes bounded sanitized tool and user outcomes into typed Evidence/FeedbackEvent; unknown input effects UNCERTAIN; Guard 7d1a2cac7cfa4f77ad56bd51183b33fa ACTIVE_VERIFIED; live 88 passed / 5 known P02 xfailed. Not wired to Engine. |
| P07 | Universal Verifier and final result gate | VERIFIED PARTIAL | P07 standalone verifier.py and tests live and exact SHA match isolated candidate; live 109 passed, 5 legacy xfailed. Guard activate returned INVALID_ARGUMENT and is NOT VERIFIED; legacy Engine not connected, false-completion remains open. |
| P08 | Runtime coordinator, shadow state machine | VERIFIED DONE (standalone) | New pure coordinator with lifecycle transitions, CAS revision, bounded retry, uncertain external action reconciliation, approval gates and checkpoint round-trip; Guard fb87e8e8b1b64c4cbc3f62e24e10f225 ACTIVE_VERIFIED, live 121 passed / 5 legacy strict xfailed; not wired to Engine. |
| P09 | Recovery/replan, action idempotency and safe retries | VERIFIED DONE (standalone) | New ActionLedger with SQLite intent reservation, CAS, retry caps, R2/R3 approval and unknown-effect reconciliation; Guard 842c1d4f97a74ee78f1def19e5496797 ACTIVE_VERIFIED, live 135 passed / 5 legacy strict xfailed. Not wired to Engine. |
| P10 | Incorporate new user messages mid-task | TESTED CANDIDATE / DEPLOY BLOCKED | Candidate 048ae76362c74b38b1cb60663a454e1d, 2725a9c387594409b95d615d9999739b rev2: 105 passed, 5 legacy xfailed. No Guard LIVE or Engine integration. SelfDevelop objective stale and normal task failed ReadTimeout; see 2026-11-15 checkpoint. |
| P11 | Traces and status UI | NOT_STARTED | Model/phase timings, decision summaries, no raw chain-of-thought. |
| P12 | Deterministic browser/desktop fast path | NOT_STARTED | Preserve native Qt screenshot optimizations. |
| P13 | Reasoning router and DeepSeek/cloud adapters | NOT_STARTED | Capability/health/permission/cost gates; shadow first. |
| P14 | E2E, fault/security, rollback and release | NOT_STARTED | All target metrics measured and evidenced. |

## Git and preservation constraints: VERIFIED INITIAL AUDIT
Project: E:/AI/repos/local-agent-hub.
Initial branch: main.
Initial HEAD: 0d54c86bfbe699004cb6c45b70297835568a9aca.
P00 inspection was read-only. **Pre-existing, NOT OWNED BY THIS INITIATIVE**:
Tracked dirty: hub/action_routes.py, hub/browser_policy.py, hub/conversations.py, hub/engine.py, hub/mcp_gateway.py, hub/model_settings.py, hub/static/action-routes.js, hub/static/app.js, hub/static/index.html.
Untracked: hub/browser_goal_board.py, hub/goal_board_api.py, tests/test_browser_goal_board.py, tests/test_goal_board_api_ui.py, tests/test_multilingual_task_sequence.py, tests/test_universal_goal_board.py.
Found existing modules: hub/engine.py, hub/browser_goal_board.py, hub/browser_completion.py, hub/delegation.py, hub/bridge_controller.py, hub/store.py, hub/model_settings.py. Found 224 test_*.py files.
New OWNED files only: docs/agent-runtime-v2/MASTER_PLAN.md and docs/agent-runtime-v2/PROGRESS.md.
Do NOT reset, stage, overwrite or commit unrelated changes. A new chat MUST inspect git status before acting because the working tree may change independently.

## Historical achievements, NOT proof of new runtime V2
Prior work improved Qt 6.11.3 browser isolation, JavaScript rendering for local SPAs, native Qt observation/screenshots, OAuth callback redaction and connected Ember Video YouTube. Prior Git commit 0d54c86... included 22 browser/Qt files, with 63 focused tests at that time. These are compatibility requirements, not P02-P14 completions.

## Immutable operating rules for every future contributor
1. Read MASTER_PLAN and this PROGRESS file first.
2. Independently verify state, timestamps and source before editing.
3. Log IN_PROGRESS / BLOCKED with exact status; mark DONE only after tests and objective read-back.
4. Keep phase history append-only. If correction needed, append superseding journal entry rather than concealing earlier failure.
5. Record exact touched paths, commands, test counts, task IDs, Git commits, Guard updates, health and release flags. Never record secrets.
6. Persist the NEXT ACTION after each bounded step. If an action is uncertain, inspect the current effect; do not replay automatically.
7. Use Guard candidate/test/deploy route for running source. Avoid more than one competing writer on the same repo files.
8. A previous chat's "done" without actual evidence is NOT enough.

## Change journal (append a new entry for each verified step)
### 2026-11-15 P00 initial Git/source inspection
Status: VERIFIED PARTIAL (not all baseline work).
Task: 93c9bf11b889468c908e4afb62c95daa; exit 0, review approved.
Evidence: main HEAD 0d54c86..., listed dirty/untracked paths, source presence and 224 test files.
No source writes or Guard deployment.

### 2026-11-15 P01 master plan bootstrap
Status: MASTER FILE CREATED, full P01 not yet verified.
Task: d18e4d376d9b44eb8a18f54895719b85; exit 0, review approved.
Output: MASTER_CREATED 10908 bytes SHA256 AB994EC2E6D449F2390769A62A0C50BEEBF994C7F956362B04117F9BF120B161.
Result: English master plan present on local Windows disk. No source files changed.
Next: create PROGRESS, independently read both, update P01 checkpoint.

## EXACT NEXT ACTION for a new chat without history
1. Read MASTER_PLAN.md and this PROGRESS.md; verify git status and active tasks.
2. P01 is VERIFIED DONE. P00 source/schema baseline and 20 passed/1 skipped tests verified; current loaded Ollama models 0 and saved delegation profiles 0. Next build P02 isolated acceptance fixtures; do not rewrite existing engine/Goal Board.
3. Capture SQLite tables/columns (NO row values/secrets), configured model/providers and acceptance benchmark requirements; append evidence and a new NEXT ACTION.
4. Preserve the pre-existing dirty Goal Board/UI/engine files; do not stage or overwrite them.
5. Start isolated P03 contracts only after baseline and source audit, with candidate tests and Guard review for runtime changes.
Copy-paste prompt for a different assistant:
"On the Windows MellowCodex project, first open E:/AI/repos/local-agent-hub/docs/agent-runtime-v2/MASTER_PLAN.md and PROGRESS.md. Read them fully. Independently verify git HEAD/status, active tasks and relevant source. Resume ONLY the exact NEXT ACTION in PROGRESS.md, preserve all uncommitted edits and Guard permissions. After completing one step, update and re-read PROGRESS.md with actual evidence, new next action and any blocker. Communicate with the human in Hebrew, with local agent instructions in English. Do not rely on chat history or invent completion."
### 2026-11-15 P01 independent file read-back and checkpoint
Status: VERIFIED DONE.
Readback task: 56f3cbe329424a06bf104811905fdcd9; exit 0; director review approved.
MASTER_PLAN.md: 10908 bytes, 99 lines, SHA256 AB994EC2E6D449F2390769A62A0C50BEEBF994C7F956362B04117F9BF120B161.
PROGRESS.md initial: 9003 bytes, 92 lines, SHA256 2A1E0779C7807DD94B350461E8F9DDE2B097C6ABAEC16CA29A55E6D19AB75AB7.
Both UTF-8, mandatory sections present, Git scope new docs/agent-runtime-v2 only, prior HEAD unchanged.
Next: P00/P02 current source and test baseline, then persist concrete results here. No runtime deployment in P01.

### 2026-11-15 P00/P02 existing test baseline and module inventory
Status: VERIFIED PARTIAL. P02 benchmark suite and full acceptance are NOT complete.
Task: 556d5813fcde4f2f8647dca582792971; exit 0, reviewed.
Command: E:/AI/tools/hub-venv/Scripts/python.exe -m pytest -q tests/test_browser_goal_board.py tests/test_goal_board_api_ui.py tests/test_universal_goal_board.py tests/test_delegation.py
Result: 20 PASSED, 1 SKIPPED in 2.74 seconds (PowerShell elapsed 3.66 seconds). No test errors.
AST-only source inventory: hub/engine.py has class Engine; hub/browser_goal_board.py contains BoardStore and goal-state functions; hub/goal_board_api.py provides router; hub/browser_completion.py has close helpers; hub/delegation.py defines Profile/Delegation; hub/bridge_controller.py contains BridgeController; hub/store.py defines Store. Actual behavior must still be inspected.
Git HEAD remained 0d54c86bfbe699004cb6c45b70297835568a9aca; all pre-existing source changes preserved, no deploy.
P01 update had one recoverable PowerShell File.Replace(null backup) failure; corrected on same task 41b6b9662a4e4af9a656c39bef2fbd90 with SHA-CAS Python os.replace, exit 0, fresh read-back. No unverified duplicate changes.
Next: inspect SQLite schema (metadata only), model/provider availability and acceptance suite gaps; do not mark P00/P02 fully complete.


### 2026-11-15 P00 read-only SQLite schema and model/provider audit
Status: VERIFIED PARTIAL. Full P00 benchmark and end-to-end integration still pending.
Task: 3acc3bc04e4645e1b24b47b4c274b2e6; exit 0, director review approved.
Source: E:/AI/state/hub.sqlite3 opened in SQLite mode=ro; 50 existing tables total.
Existing authoritative structures confirmed: tasks(id,idem,revision,state,goal,criteria,checkpoint,...), actions(id,task_id,tool,args,state,result,created), events(seq,task_id,revision,kind,data,at), browser_goal_boards(task_id,revision,board), context_working_state(task_id,revision,watermark,task_revision,data), delegation_profiles(id,data), delegation_runs(id,request_id,chat_id,data,revision), development_guidance(task_id,revision,epoch,consumed_epoch,...).
No tables with agent_ prefix exist. No row values/user content accessed, no DB writes.
Live MellowCodex model_memory_status: loaded=false, models=[] (this DOES NOT prove models absent from disk). delegation_profiles: 0 configured entries; no proven DeepSeek/cloud reasoning provider configured.
Design implication: P03/P04 must reuse the existing tasks/actions/events and browser_goal_boards, adding only compatible versioned structures after exact source inspection, not replacing existing DB.
Next: P02 acceptance fixtures; do not prematurely claim universal routing or success verifier completion.


### 2026-11-15 P01 Git durability checkpoint
Status: VERIFIED DONE.
First document publication task a8bdeb0fdabf49ed81a68f8adca92a1d: CRCRLF line ending issue corrected before commit, only MASTER_PLAN.md and PROGRESS.md staged; git diff check passed; commit 82d116790f200d70702e4e589d2bbbaf059eb302 pushed non-force to origin/main, confirmed by git ls-remote.
All 15 pre-existing dirty source and test paths remained untouched.
This new journal entry is a follow-up publication: latest Git revision must be read from git log/origin/main, not inferred from the first commit ID.
Next action: P02 isolated safe acceptance fixtures; Walla homepage alone MUST NOT satisfy a login-form goal, then test other multi-step browser and desktop objectives. P00/P02 still PARTIAL.


### 2026-11-15 P02 acceptance fixture candidate, Guard and live verification
Status: VERIFIED PARTIAL; do not mark P02 done until unresolved strict XFAILs and benchmarks are closed.
Candidate task: 0b817fbffeeb4380a1baf53b378702b5; candidate 2a52ba0b21674e86a202f9ecc00f6b93 rev1; two NEW files only:
- benchmarks/agent_runtime_v2/acceptance_v1.json (32 synthetic browser/code/desktop/inspect cases; no live credentials)
- tests/test_agent_runtime_v2_acceptance.py (parameterized baseline + strict known-gap xfails).
Candidate test: 46 PASSED, 1 SKIPPED, 5 XFAILED.
Guard deployment id 73fb7d73542c4672830052ea65a44aff: ACTIVE_VERIFIED independently read after transport returned INVALID_ARGUMENT. Do NOT blindly repeat activation.
Live read-back task c20361135b134133a2d53e93fcc54331 exit0; exact local paths present, pytest: 46 passed, 1 skipped, 5 xfailed in 1.36s, all source edits untouched.
New file SHA256: JSON 463AA23DD891BC7464BD488CF27CF510300011A88E2D8C9A005685754943A905; test 5F6DF4AAC2328D76E35E3A1910906DBC5E5A07656A780FF6E45A13C10AC1747F.
Known defects recorded: B15/B16 wrong-domain or lookalike password form can be accepted after assess; B24 read-only generic search marked done despite unmet goal; C02/D01 generic code/desktop task_state=done can override missing acceptance evidence.
NEXT: P03 typed contracts additive, no edit of dirty Goal Board/engine; then P04 persistence and P07 verifier to make strict xfails genuine passes. P02 perf/E2E baseline remains pending.


### 2026-11-15 P03 typed contracts deployed and verified
Status: VERIFIED DONE for typed contract definitions, NOT for full runtime integration.
Candidate task ce418147131a4306b0b354c1440de2eb; candidate abff583f06e74ec98803827e403b3834 revision1; three NEW files only: hub/agent_runtime_v2/__init__.py, hub/agent_runtime_v2/contracts.py and tests/test_agent_runtime_v2_contracts.py.
Contracts cover TaskPlan, versioned DAG steps and final mandatory acceptance, Pydantic validation, typed Evidence with timezone/freshness, audited DecisionRecord without raw chain-of-thought, FeedbackEvent, ActionRecord and semantic stable_action_key. Existing engine/Goal Board untouched.
Guard update b3c51b57570646429d732e9dea506e7a ACTIVE_VERIFIED, independently read after transport INVALID_ARGUMENT; no blind redeploy.
Live verification task 2f6694dcd786474eb653c8b607c55c02 exit0: 62 PASSED, 5 known P02 strict XFAILED in 1.23s; all new code/test files present.
SHA256: __init__.py A478D8D0DCD368EC458CF7E4C8FFD4AB2BD6DD36137779A9643A25BE18F9F670; contracts.py B7496B4E120C4E3046D65DDBF5F27293D2612C3938671CDE1973667BE9DB932A; test 7DD8FB40B521E7A4C800343C05EA66F22A18620D92B7D6790599011B9FE52053.
NEXT: P04 additive SQLite repository for versioned plans/evidence, with transaction/CAS/crash tests. Do not overwrite existing dirty source. P02 known gaps still require P07 verifier.


### 2026-11-15 P04 additive SQLite persistence validated in live repository
Status: VERIFIED DONE for additive repository module, NOT production engine integration or a live user-database migration.
Candidate task 94788c4bec544fe48f96e56ad2110997, candidate 1c048a8f47fe409a99673cbf24544fe6 revision2.
Only new hub/agent_runtime_v2/persistence.py and tests/test_agent_runtime_v2_persistence.py. Initial tests found Python sqlite3.executescript implicitly commits the transaction and breaks rollback; replaced with individual DDL statements under BEGIN IMMEDIATE. Candidate 73 PASSED and 5 existing strict P02 XFAILED.
Guard update 4d54969a56a14ded9161407b7f17da06 ACTIVE_VERIFIED. Live readback/test task 1ae4cee34ca44d0badf2338e5c892a7f exit0: 73 passed, 5 xfailed in 1.42s; tests use temporary databases only, do not write live hub.sqlite3.
New files sha256: persistence.py 84585487564CF46284A6FB08C53BC9C4701F5A4B3903453C13D0C6640D5CE383; test 3A733B1A9654F84D14A82C71B87F2DD02A84D7368C19F7F26635C7AC53D497AA.
NEXT: P05 Goal Board -> versioned Plan adapter with tests, then P06/P07 generalized evidence and completion. Preserve all preexisting dirty Goal Board/Engine/UI files.


### 2026-11-15 P05 editable Goal Board to TaskPlan adapter
Status: VERIFIED DONE for pure conversion module and tests, NOT integrated into active Hub Engine.
Candidate task 78eaa2959d11452daee2abb9c1baa7b0; isolated candidate df334eff787b4a3bb4bfad5f9b616cc7 rev1. Only NEW hub/agent_runtime_v2/goal_board_adapter.py and tests/test_agent_runtime_v2_goal_board_adapter.py. No changes to dirty hub/browser_goal_board.py, engine or UI.
Adapter carries goal, task_mode, target_host, feedback_mode, edited steps/alternatives/notes, original language and BoardStore revision to immutable versioned TaskPlan. Final login criterion demands both actual login form and requested hostname. It NEVER treats pre-existing task_state=done as verified completion.
Guard update 3c792bc6a6164472990b74f68a090eb7 ACTIVE_VERIFIED. Live verification task bb68021983fc48129baceb5118b2b438 exit0: 85 PASSED, 5 known P02 strict XFAILED in 1.62s. New files SHA256: adapter DEEC38690084114D8535C7D43994A4A29C3FE148377C854B1C12D5DB375B0AF5; test 7E5070710E3C69131ECFC4819410EDE3418C02776E0B107DBFDFFED2E12A4376.
NEXT: P06 evidence and feedback collector with sanitization/freshness; P07 universal verifier to close five known false-success cases, then P08 coordinator. P02 real E2E/performance remains open.


### 2026-11-15 P06 typed safe feedback and evidence normalization
Status: VERIFIED DONE for independent normalizer; not yet wired to active Engine or full completion verifier.
Candidate task 737105c5068944a5a146888d386ef536, candidate 1cd219f44c3e41649e8f95701811f8aa rev1. Only NEW hub/agent_runtime_v2/feedback.py and tests/test_agent_runtime_v2_feedback.py. No existing engine/Goal Board modified.
Normalizer converts tool/browser/desktop/file/worker/user status to FeedbackEvent and Evidence; records source, time, identity and freshness; bounds nested untrusted content; redacts OAuth query/fragments/credential keys/bearer/private reasoning; keeps dispatched-but-unverified clicks UNCERTAIN. This is tool-level confirmation only, not actual task-goal completion.
Guard update 7d1a2cac7cfa4f77ad56bd51183b33fa ACTIVE_VERIFIED. Live task 9a79ada1d35c4ad2a07d367ebcb1586b exit0: 88 passed and 5 existing P02 strict xfailed in 1.32s.
SHA256: feedback.py 6414549EAF282772737CE0897EA89A1F561E3E4496ACB74B59D5C171E56D32F5; test 7FB565F0FEB88EBBF166C4178D4F27B10A77CF74E2F3A5F64401072CB0E72369.
NEXT: P07 universal verifier and P02 known false-completion blocking suite; P08 shadow coordinator then P09 recovery.


### 2026-11-15 P07 deterministic verifier live reconciliation
Status: VERIFIED PARTIAL, not active Engine integration. No Guard ACTIVE_VERIFIED update ID exists for P07.
Candidate task 3ebcc3a649d94520acef2a6d8f8ac559, candidate d1832228774b4c2dae3df28146bb8571 revision1. Two new paths: hub/agent_runtime_v2/verifier.py and tests/test_agent_runtime_v2_verifier.py. Candidate tests 109 passed, five legacy P02 strict XFAILED.
Guard prepare_update returned INVALID_ARGUMENT. Instead of repeating uncertain deployment, live read-only reconciliation task f246a8793da447bc81776e5892e760e3 exit0 compared SHA256 and reran live tests: 109 passed, five XFAILED in 1.46s. Live verifier.py SHA e738f80e0ccdeab52d46071889f1e5b153e59c42a2e32010445afb2bb592a272; live test SHA c40b64049452bcea1930b14647173141fd65183997b1586dc6ceb2b79b2edff5. Both MATCH candidate exactly, present as untracked project files. No active Hub engine integration was performed. This module checks plan version, evidence freshness, observed correct-host login form and assessment; rejects wrong host, stale evidence, premature tool success and worker claims in its own new tests.
NEXT: P08 shadow runtime coordinator implementing plan progression without modifying dirty Engine; maintain the P02 five XFAILs as blocking legacy integration work and do not claim full task correctness.


### 2026-11-15 P08 shadow lifecycle coordinator verified
Status: VERIFIED DONE as standalone shadow-mode code; no live Hub Engine integration or real-browser E2E yet.
Candidate task 706eb53936f949f0a26d685894fb8e3d; candidate 6160868c40ac4f2483bfb72ff7545a1e rev1. Two NEW files: hub/agent_runtime_v2/coordinator.py and tests/test_agent_runtime_v2_coordinator.py; original dirty Hub Engine, Goal Board and UI untouched.
New state reducer enforces explicit CREATED -> PLANNING -> READY -> EXECUTING_STEP -> VERIFYING -> NEXT/RETRY/REPLAN/FINAL_VERIFICATION -> COMPLETED. Requires fresh P07 verifier evidence before completing steps, tracks snapshots with CAS revision and transition budget, guards R2/R3 unknown results from unsafe retries, supports user change, waiting approval, cancel, versioned replanning and SQLite checkpoint persistence readback.
Guard update fb87e8e8b1b64c4cbc3f62e24e10f225 ACTIVE_VERIFIED. Live readback/test task 477c2365475b4de0a39d377a35359b16 exit0: 121 PASSED, 5 existing P02 strict XFAILED in 1.75s. File SHA256 coordinator.py 0DCA2548A0AA9B5B5E5BCB5289B141D7107CBC8910B127E65C514A3EC765195F; test 2B463F1C498BDEDE58BA3EA86322DA03500F855482B70668FAEF2B93607CD28C.
NEXT: P09 bounded retry/replan/idempotency/reconciliation module with fault injection. Then P10 live user-correction plan merge; P11 telemetry and UI; P12 deterministic path; P13 model routing; P14 E2E and production release. Do not claim user objective success until remaining integration and 5 legacy XFAILs resolved.


### 2026-11-15 P09 durable action ledger, bounded recovery and reconciliation
Status: VERIFIED DONE as standalone library and tests. NOT yet integrated into active Hub Engine or actual user database.
Candidate task 64e355edb9534a618721b682b2435a77, candidate 6e64f89bfc8d4f038d1cae6fa56120e0 rev1. Two NEW paths only: hub/agent_runtime_v2/recovery.py and tests/test_agent_runtime_v2_recovery.py. No changes to dirty legacy Engine, Goal Board or UI.
ActionLedger adds opt-in agent_action_intents SQLite table, stable semantic effect ID across plan revisions, atomic reservation and dispatch, risk-dependent R2/R3 approval, idempotent applied-effect suppression, evidence-required reconciliation of unknown outcomes, proof of non-effect before bounded retry, and no raw target/arguments/credentials saved in the ledger.
Guard update 842c1d4f97a74ee78f1def19e5496797 ACTIVE_VERIFIED. Live verification task 9e4e819983af4076a8ca9a07085a08ed exit0: 135 PASSED, 5 prior strict legacy P02 XFAILED, 2.33 seconds pytest.
Source SHA256 recovery.py 4EAA62F967C68452FF035E81817CBD986FDF58E9FECDE3D234CE8D33A4F4B88C; test SHA256 D088FC9D620A19B42B5D553015687D48B51568AA63BF2CF58F24887E806589D1.
NEXT: P10 user instruction integration and plan versioning, P11 trace/visible progress, P12 deterministic executor, P13 model reasoning router, P14 E2E/security/release. P02 legacy false-completion cases and active Engine integration remain blocking.


### 2026-11-15 P10 TESTED / NOT DEPLOYED: control-plane blocker
Status: VERIFIED TESTED CANDIDATE, DEPLOYMENT BLOCKED; P10 is NOT DONE and no real Engine integration was performed.
Source: P10 candidate task 048ae76362c74b38b1cb60663a454e1d, candidate 2725a9c387594409b95d615d9999739b revision 2 (staged). New standalone source/test: hub/agent_runtime_v2/guidance.py and tests/test_agent_runtime_v2_guidance.py; no legacy Engine/UI/Goal Board overwrite claimed.
Test evidence: revision 1 96 PASSED and 5 legacy strict XFAILED; revision 2 candidate_test exit 0, verified true, 105 PASSED and 5 legacy strict XFAILED in 1.96 seconds. Do not assume rev2 deployed merely because candidate tests passed.
Control-plane blocker: the existing MellowCodex SelfDevelop session still has an obsolete Guard-repair original objective from 2026-11-14. P10 review/prepare encountered INVALID_ARGUMENT. Switching to normal mode worked (mode revision 41), but restarting SelfDevelop with the P10-P14 objective returned INVALID_ARGUMENT. A new normal-mode task in the same local conversation (073a1e73947a45e193ce4379d8e72011) repeated file reads and ultimately FAILED with engine_run ReadTimeout after 35 recorded completed tool actions. Chat mode return to selfdevelop was refused HTTP 409: Finish or review all active tasks. The failed task still appears in active_tasks, with no evidence of any file mutation or external effect from those reads. Do not mark blocker resolved.
Durable project file updated through the authenticated GitHub connector on origin/main because local mode transition blocked a Windows command. This is a documentation commit ONLY, not a deployment. Local Windows checkout last observed HEAD f95c3224bea285153f90746e35d3fecae349b283 with pre-existing dirty changes; remote will be ahead after this checkpoint, so fetch and reconcile before any further local commit/push; NEVER force-push, reset or discard user changes.
NEXT EXACT SAFE ACTION: inspect failed task 073a1e73947a45e193ce4379d8e72011 and clear its terminal-mode blocker through a documented, authorized task lifecycle procedure. Do not cancel/replay uncertain external actions. Rebind the authorized SelfDevelop objective to Runtime V2 if supported, then verify and deploy P10 through Guard with active-code readback and targeted tests. After each subsequent P11/P12/P13/P14 step, update this PROGRESS file. Overall release acceptance gates, 5 legacy P02 false-completion XFAILs and real Engine wiring remain open.
