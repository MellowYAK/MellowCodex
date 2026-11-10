# SelfDevelop director handoff - 2026-11-08

Goal: supervised and autonomous self-repair/upgrades through the local agent, with evidence, review, bounded corrections, controlled activation and reconnect. Not complete.

External supervisor chat: https://chatgpt.com/c/6af06666-2b34-83eb-ac17-6fdabb2b5b93
Project ID: 6b4507f4f34c41e8b4113d2b4dccc394
Workspace: E:/AI/repos/local-agent-hub

## Observed production state
Mellow Guard updates e18975c0d6d04ef5817122f95f06e846 and f5995da5020e4875b7c9b4f13febe682 reached ACTIVE_VERIFIED. The first preserved command guards, strengthened timeout validation, and added permanent worker preservation instructions (22 focused tests). The second forwards latest persisted exact-command correction reason/request_id into worker packets (7 focused tests). Earlier documentation entries marked pending describe pre-activation checkpoints; these deployment receipts supersede that pending state only.

## Current defect and next bounded task
correct() in hub/development/commands.py calls command.strip() before checking command type. Add not isinstance(command,str) BEFORE command.strip(), retaining shell validation, length/blank validation, timeout checks and all unrelated source. Add a NEW test file for command None/123/True, requiring ValueError with task revision unchanged. Preserve existing tests. Run tests/test_selfdevelop_commands.py, tests/test_correction_timeout_contract.py and the new test only. Review actual diff, not only green tests.

Rejected candidate 5e59b3bbca2e4f97b80f3ab7923d4438 revision2 is evidence only, DO NOT ACTIVATE. Qwen Coder7B removed shell validation and the module docstring. 1 failed/20 passed. Exact director correction then returned unchanged source. Trial eccf24f2a4f74e129c2497bf14c27f47 was cancelled and model unloaded. This is NOT autonomous success.

## Workflow
New external chat must create its OWN stable binding with sync_conversation_message; never reuse old chat IDs solely for project ownership. Discover actual MCP tools. Use project map/search and bounded source reads. All edits through local agent; director may supply exact patch when model fails. Do not repeat unchanged failed proposals. Keep durable critique plus original goal, test outputs and diff. Candidate is not activation. Use Mellow Guard product prepare/activate/status and verify reconnect; no direct process-kill fallback. Preserve dirty worktree and private state. Never print credentials. Publish coherent validated changes through agent after inspecting staged content, no bulk staging or force-push.

## Remaining acceptance
Prove new external GPT MCP chat executes repair -> reports evidence -> receives correction -> fixes -> director approves -> production activates -> MCP reconnects. Independently verify autonomous local planning/repair; currently unproven. Desktop and dependency upgrades are not covered by current control-plane scope. Then test real image-from-chat ingress with exact bytes/hash/path; do not substitute unrelated image downloads.

## Latest delegation observation
The new browser chat accepted the handoff and displayed a pending response, but no new local binding/task was observed at this checkpoint. MCP list_projects_and_chats independently returned in under one second. A handoff alone is not proof of execution.
