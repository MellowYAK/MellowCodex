# MellowCodex Agent Runtime V2 — VERIFIED PROGRESS AND RESUME LOG

THIS IS THE SINGLE MOST IMPORTANT FILE FOR A NEW CHAT OR MODEL. Read MASTER_PLAN.md beside this file, then read this checkpoint and independently check live Git and system state. Do not depend on prior ChatGPT conversations, model memory or verbal claims.

## Current checkpoint (as last recorded)
Project status: IN PROGRESS, not production-complete.
Last session date: 2026-11-15.
Current milestone: P04 additive SQLite plan/evidence/checkpoint repository VERIFIED DONE (new module only); P05 Goal Board adapter and P06/P07 verifier next.
Last VERIFIED milestone: P01 durable master/progress VERIFIED DONE; P00/P02 audit and baseline VERIFIED PARTIAL.
Master document creation: task d18e4d376d9b44eb8a18f54895719b85, exit 0, 10,908 bytes, SHA256 AB994EC2E6D449F2390769A62A0C50BEEBF994C7F956362B04117F9BF120B161.
PROGRESS document: VERIFIED CREATED and independently read back (task 56f3cbe329424a06bf104811905fdcd9, exit 0).
Next action: P05 implement an additive adapter from existing hub/browser_goal_board.py into versioned TaskPlan with acceptance criteria, without changing dirty Goal Board/Engine/UI. Then P06 evidence collection and P07 universal verifier to close known P02 false completions.

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
| P05 | Universal adapter to existing Goal Board | NOT_STARTED | Uncommitted Goal Board code needs provenance review. |
| P06 | Tool/browser/desktop/user feedback and evidence | NOT_STARTED | Freshness, provenance, OAuth sanitization. |
| P07 | Universal Verifier and final-completion gate | NOT_STARTED | Require verifiable acceptance evidence. |
| P08 | Runtime state machine SHADOW implementation | NOT_STARTED | Old engine remains authoritative until verified. |
| P09 | Bounded retries, recovery and replanning | NOT_STARTED | Idempotency and unknown-outcome reconciliation. |
| P10 | Incorporate new user messages mid-task | NOT_STARTED | Versioned revision and no duplicate actions. |
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
