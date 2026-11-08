# 0.18.0: GPT-explicit preflight recovery bootstrap

## Approved source and receipt
Five paths only: hub/development/selfdevelop.py, hub/development/service.py, hub/development/api.py, hub/development/tools.py and tests/test_selfdevelop_preflight_recovery.py. Approved candidate 5a6d8a40174a4c75989221a2319c0a77 rev14. Existing receipt test-ba7b4ec6e2a34bd5bd591bf0254330d8.json: 30 passed in 15.23s; verified=true; source_changed=[]. Independent B approval covers exactly these files.

## Verified installation
Guard 9a4ef1f526904a22b84bd624fd5d8159 is ACTIVE_VERIFIED. All five installed bytes match Guard and candidate SHA-256 hashes. This is verified bootstrap installation and owned service health, NOT proof of positive live recovery or deployment of all 0.18.0 release metadata.

## Contract and safety boundary
GPT alone directs through MCP, with exact local execution. Recovery requests use the existing original chat and objective and select explicit narrow/exact modes. Failure-time packet digests and historical source bytes are anchored; unanchored legacy runs, uncertain effects and source drift are rejected. Narrow mode cannot expand authorized scope. Exact mode records verified test receipt and review state atomically, then requires separate external GPT semantic review. No local-model director, automatic remediation, autoapproval, replay of uncertain effects, or automatic Guard activation.

## Known limitations
No positive real recovery run has yet been demonstrated, so do NOT mark recovery accepted end to end. The previously verified GPT-guided exact MCP installation in chat 8cae5657612a4fbeb390c51a8201fb64 is a distinct completed task. The experimental automatic selfdevelop_run_objective run failed before writing at context budget and remained reconcile_required; this does not retroactively negate guided acceptance. Publication is PR source only; no merge or separate deployment by C.
