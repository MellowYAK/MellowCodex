# MellowCodex Agent Runtime V2 — VERIFIED PROGRESS AND RESUME LOG

THIS IS THE SINGLE MOST IMPORTANT FILE FOR A NEW CHAT OR MODEL. Read MASTER_PLAN.md beside this file, then read this checkpoint and independently check live Git and system state. Do not depend on prior ChatGPT conversations, model memory or verbal claims.

## Current checkpoint (as last recorded)
Project status: IN PROGRESS, not production-complete.
Last session date: 2026-11-15.
Current milestone: P00 SQLite/model/source BASELINE VERIFIED PARTIAL; P02 acceptance fixture design and tests next.
Last VERIFIED milestone: P00 read-only Git/source audit PARTIAL, task 93c9bf11b889468c908e4afb62c95daa, exit 0, approved.
Master document creation: task d18e4d376d9b44eb8a18f54895719b85, exit 0, 10,908 bytes, SHA256 AB994EC2E6D449F2390769A62A0C50BEEBF994C7F956362B04117F9BF120B161.
PROGRESS document: VERIFIED CREATED and independently read back (task 56f3cbe329424a06bf104811905fdcd9, exit 0).
Next action: P02 create isolated safe acceptance fixtures for Walla homepage-versus-login and selected multi-step tasks, using existing Goal Board/verifier tests; measure acceptance failures and performance before modifying engine. Preserve all dirty source files.

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
| P02 | Acceptance fixtures and benchmarks | IN_PROGRESS | Initial existing test baseline verified: 20 passed / 1 skipped (2.74s pytest), task 556d5813fcde4f2f8647dca582792971. Full 20+ flows, timings and negative cases remain. |
| P03 | Typed TaskPlan/Step/Evidence contracts | NOT_STARTED | Inspect exact existing schemas and tests first. |
| P04 | Additive SQLite plan/event/checkpoint persistence | NOT_STARTED | No destructive migrations. |
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
