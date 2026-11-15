# MellowCodex Agent Runtime V2 — MASTER PLAN

Document status: CANONICAL DESIGN SPECIFICATION. Implementation progress is recorded in PROGRESS.md. Write all technical agent handoffs in English. User-facing responses remain in Hebrew.

## START HERE: Instructions for a brand-new agent or model
1. Read E:/AI/repos/local-agent-hub/docs/agent-runtime-v2/MASTER_PLAN.md and PROGRESS.md completely.
2. Independently check git status, git HEAD, live services, Guard status, active tasks, actual files and tests before acting.
3. Continue ONLY the next unblocked step recorded in PROGRESS.md. Do not rely on old chat memory.
4. Perform one bounded step, verify its effects, and update PROGRESS.md with exact task IDs, file paths, test commands/results, commit/deployment IDs and the NEXT ACTION.
5. Never mark a step complete on model narration alone. If verification fails, record PARTIAL/BLOCKED, reason, and safe recovery.
6. Preserve pre-existing dirty files, chats, projects, SQLite history, Guard/OwnerBroker policy, browser profiles, credentials, services and GPU/model settings. Never reset, overwrite or stage unrelated work.
7. Use isolated candidate + tests + existing Guard deployment for source changes; no unapproved elevation or silent retries of uncertain side effects.
8. Before finishing a turn or changing chat/model, ensure PROGRESS.md has the latest verified checkpoint and a standalone continuation instruction.

Repository: E:/AI/repos/local-agent-hub
Public remote from prior verified work: https://github.com/MellowYAK/MellowCodex
Canonical documents: docs/agent-runtime-v2/MASTER_PLAN.md and PROGRESS.md

## Final goal
Deliver a fast, safe, reliable, autonomous MellowCodex runtime for browser, Windows, files/code and MCP. It must infer the actual requested end state, build a persisted versioned plan, execute and observe tools, verify evidence, recover or replan, accept user corrections in flight, use appropriate local and optional cloud reasoning, enforce permissions, and resume across process/chat/model restarts without duplicate unsafe actions.

Never treat "opened the website" as completion when the request is "show the login form."

## Measurable definition of done
- At least 95% goal success on a published beta acceptance suite.
- Zero false completions on the blocking negative suite, including Walla homepage versus real login form.
- Zero unauthorized R2/R3 operations and zero duplicate external side effects under injected failures.
- Simple 2–3-step browser workflow: p50 < 6 seconds, p95 < 15 seconds measured over at least 100 runs on a specified warm reference machine.
- Known deterministic action sequences: zero LLM calls while preconditions and observations remain fresh.
- 100% of the bounded crash-resume and mid-run-user-correction test cases pass.
- Model routing selects only available, compatible, permission-approved providers and respects context, privacy, latency and cost limits.
- Every test task has traceable plan version, chosen model, action, result, evidence, verifier outcome and final status.
- Feature-flag rollback demonstrated, preserving existing SQLite history and user work.
These are proposed RELEASE GATES, not current achievements.

## Existing implementation: preserve and reuse
Known project modules include hub/engine.py (tool/inference loop), hub/store.py (SQLite), hub/browser_goal_board.py and hub/goal_board_api.py (browser checklist), hub/browser_completion.py (partial goal verification), hub/browser_workflow.py, hub/delegation.py, hub/bridge_controller.py, hub/model_settings.py, Guard and OwnerBroker.
Earlier verified browser work includes Qt 6.11.3 isolated GUI, fast native screenshots, local-JavaScript preservation, OAuth URL redaction and multiple regression tests. Keep these fixes.
The deep research supplied by the user is a DESIGN INPUT, not proof every component exists. Inspect exact source and tests first. In particular, Engine.chat think=False is a previously observed default, but do not assume current branch implementation or installed DeepSeek/cloud profiles.
A read-only audit on 2026-11-15 found HEAD 0d54c86bfbe699004cb6c45b70297835568a9aca and many UNCOMMITTED modifications in engine, goal-board and UI modules. See PROGRESS.md. Do not overwrite or commit them without understanding ownership.

## Target architecture
User/Chat/PLAY/MCP -> GoalNormalizer -> TaskPlanner -> versioned TaskPlan -> RuntimeCoordinator -> (PolicyEngine + ReasoningRouter + ToolExecutor) -> FeedbackCollector -> EvidenceStore -> UniversalVerifier -> (next step / retry / replan / user / approval / fail) -> FinalVerifier -> COMPLETED.
Components:
- TaskPlanner: explicit objective, dependencies, constraints and acceptance criteria. Cheap path for trivial tasks.
- RuntimeCoordinator: authoritative state transitions; no early completion, bounded loops, cancellation and checkpoints.
- ModelRegistry and ProviderAdapters: Qwen/Ollama local, DeepSeek local/API, optional cloud; capability, availability, context and privacy checks.
- ReasoningRouter: deterministic no-model, fast local, deep local, cloud escalation only if authorized and justified. Begin in shadow mode.
- ToolExecutor: reuse Qt/Playwright, Windows, files, coding tools, MCP and existing permissions.
- FeedbackCollector: SUCCESS, FAILURE, UNCERTAIN, USER_OVERRIDE; connect actual effect to every action.
- EvidenceStore: source, timestamp, target identity, freshness, content hash, sanitized payload and tool call ID.
- UniversalVerifier: deterministic acceptance checks and final gate. LLM final text alone is not sufficient.
- Recovery/Replan: bounded retries, deduplication, plan revision, safe resume after lost tool acknowledgement.
- GuidanceMerger: classify new user message as clarification, correction, extension or new task, preserve completed valid steps.
- Telemetry/UI: task checklist, model routing reason, stage metrics, concise decision records (not raw hidden reasoning).

Required lifecycle:
CREATED -> PLANNING -> READY -> EXECUTING_STEP -> COLLECTING_EVIDENCE -> VERIFYING.
Verifier outcome: SUCCESS -> NEXT_STEP; transient -> bounded RETRY; mismatch/user change -> REPLAN; missing permission -> WAITING_APPROVAL; missing user input -> WAITING_USER; irrecoverable -> FAILED.
All required criteria pass -> FINAL_VERIFICATION -> COMPLETED. UNCERTAIN is not success.

## Typed contracts and storage
TaskPlan(task_id, version, goal, constraints, steps, final_criteria, creation_revision, status).
PlanStep(id, plan_version, objective, dependencies, permitted_tools, acceptance, retry_policy, max_model_turns, latency_budget, state).
AcceptanceCriterion(id, verifier_type: dom/url/visual/file/process/structured/user/custom, expected, required, evidence_freshness_ms, risk).
Evidence(id, source, observed_at, tool_call_id, target_id, content_hash, freshness_deadline, sanitized_payload).
ActionRecord(id, idempotency_key, task_id, step_id, risk, dispatch_state, observed_result).
DecisionRecord(decision, reason_code, evidence_ids, selected_strategy/model, elapsed_ms). Never expose private chain of thought.
Use additive SQLite migrations only after examining current schema. Existing messages/tasks/actions/events remain authoritative until the new engine is proven. Feature flag defaults OFF. Never delete existing data for migration.

## Risks and permissions
R0 read-only; R1 reversible; R2 external side effect; R3 destructive/financial/security. Enforce via Guard/OwnerBroker, not just model suggestions or MCP annotations. Browser pages and worker outputs are untrusted. Redact tokens/OAuth URLs. If an external action might have executed but the acknowledgement is lost, RECONCILE before retry; do not automatically repeat it. Provider fallback cannot bypass privacy or spending policy.

## Ordered implementation packages
P00. Audit baseline, Git provenance, code, DB schema, running tasks/models/services and previous tests.
P01. Durable master plan + progress checkpoint, on-disk read-back and Git preservation.
P02. Build versioned acceptance/benchmark suite (20+ flows; Walla login, Windows, files, corrections, errors) and capture p50/p95 baseline.
P03. Add typed agent contracts and serialization/versioning tests, reusing existing types.
P04. Add additive plan/evidence/event persistence, optimistic concurrency, durable checkpoints, migration tests.
P05. Adapt existing Goal Board to universal TaskPlan without replacing its browser UI or prior work.
P06. Collect normalized browser/desktop/user/tool/worker feedback and sanitized, fresh evidence.
P07. Create universal criterion verifier and final-success gate, prove no Walla-homepage false completion.
P08. Runtime state machine in SHADOW mode; old engine remains authoritative until verified.
P09. Bounded recovery/replan, action idempotency, uncertain-effect reconciliation and test fixtures.
P10. Merge new user messages into active versioned plan without losing valid completed steps.
P11. Structured traces and visible progress/feedback in chat/UI; measured per-stage latency.
P12. Deterministic browser/desktop fast path; preserve current native Qt screenshot and Playwright mechanisms.
P13. Model registry, local reasoning policy, DeepSeek-compatible provider, optional cloud, shadow routing then guarded rollout.
P14. Fault/security/performance E2E validation, Guard deployment, rollback drills, docs and release gates.

Sequence and dependencies: P00/P01 -> P02 -> P03 -> P04 -> P05/P06 -> P07 -> P08 -> P09/P10 -> P11/P12 -> P13 -> P14. Security and tests are continuous. Use small isolated candidates and focused tests for every code change, not a one-shot rebuild.

## Mandatory test matrix
Browser login (positive and negative), stale DOM, refresh/reconnect, navigation; multi-step Windows task verified by actual window state; file/code edit and read-back; injected 429/500/model failure; unauthorized action refusal; uncertain external tool result; crash/resume and action dedupe; live mid-task correction; provider routing/fallback; 100-run latency and full causal trace; Guard rollback and preserved user state.
Every item requires exact commands, exit status, observations and retained evidence. Document reproducible failures rather than claiming completion.

## Update discipline
After each bounded step: record [date UTC, P-ID, status, exact changes, affected paths, commands, pass/fail, task/commit/Guard IDs, risks, next action] in PROGRESS.md, verify by fresh disk read-back, then proceed. Keep old journal entries. If Git is dirty, commit ONLY explicitly owned files, never blanket git add.
New chat handoff prompt: "Read both canonical files, verify live repo and service state, continue the single NEXT ACTION in PROGRESS.md, then update and verify progress with factual evidence before replying. Do not repeat uncertain side effects."