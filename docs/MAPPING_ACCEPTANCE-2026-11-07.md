# Supervised project mapping acceptance — 2026-11-07

## Requested outcome
A new GPT conversation can discover a local project, navigate its indexed source and relationships, request original ranges, and direct bounded execution with returned evidence. Git is optional. Mapping does not authorize running the mapped project or implementing new features.

## Evidence and limits

| Requirement | Observed evidence | Limit |
|---|---|---|
| Source inventory | Independent coverage audit: 310 eligible Ember Video files and 310 indexed files | Source policy excludes dependency trees, models, media, secrets and other non-source files; not an all-disk count |
| Incremental analysis | Live UI: 310 unchanged, zero changed/deleted, revision 1; earlier refresh reused all 310 analyses | Refresh still hashes source bytes; it is not Git history |
| Map and relationships | Measured overview: 1689 Python symbols, 214 AST files, 95 text files, one syntax-error file; PLAY related-source request returned evidence | Import/test relationships are navigation candidates, not verified runtime dependencies; install_qwen.py has a source syntax error |
| Search and original source | Current production UI search `save projects.py` found ember_video/projects.py and opened its save/revision implementation | No project code executed |
| New-chat MCP discovery | GPT conversation ending 9872-a7389d4c9b7a used project_context, context_search and context_expand; three server HTTP receipts; read projects.py lines 120–206 | New convenience wrappers were not required; cached client catalogs may not show them |
| Automatic PLAY director cycle | Linked local chat e249a777ce6d46bbb6a28bf2820991b1: brief, related metadata, exact source ranges, then GPT's source-backed map | This is mapping acceptance, not universal autonomous task correctness |
| Exact evidence | Five returned PLAY source hashes independently matched files on disk | Historical receipts do not certify a later changed file |
| Review boundary | Real runner tasks ended waiting_review; controller reached review_ready after director response | Local-only Qwen semantic reasoning remains unaccepted; generic natural-language tool execution is not universally deterministic |
| Resource use | Deterministic mapping/source steps made no local inference calls; Ollama reported zero loaded models after acceptance | Optional local coding tasks may load a configured model |
| Continuity | PLAY reused the linked conversation; normal restart retained it and left the completed bounded run stopped | No claim that every provider or browser failure is recoverable |

Live PLAY tasks: 973b29dbce5942679acfac676933a125, 06dd978fe882467fb6c70b4f33510aa5, 6a75df94c60249af9765dbb7ffefc5a8. The first two exposed an unnecessary rejected bootstrap read; the final cleanup skips that bootstrap for context_read. Three focused fixtures passed; cleanup was loaded by normal restart.

Audit artifacts are retained locally, not published: `E:/AI/audits/recovery-directed-20261107/`: map-coverage-audit.json, play-map-runner-evidence.json, play-map-director-final.txt, play-map-source-hash-check.json, mcp-map-access-receipts.json. Source and conversation payloads remain outside Git.

## Division of work
GPT chooses the next bounded step and reviews original evidence. The executor returns results, errors and missing evidence. Exact map/source/patch requests bypass local paraphrasing. Director review is distinct from human approval; an unavailable director is not permission to switch silently to autonomous work. The shared instruction was clarified and 19 protocol/guidance fixtures passed in 2.88 seconds. This is not a claim that instructions alone enforce every generic action.

## Provenance and remaining broader work
The fast index and recovery/director changes are native Hub work. APC-derived baseline metadata contracts remain separate; provenance is in apc-reuse-manifest.json. No new APC browser or other tool implementation was imported for this release.

The original broad product plan, universal self-development, full UI polish, Guardian activation/rollback and optional Git-assisted feedback are not declared complete by this mapping acceptance. Source version 0.15.0 publication and remote verification are recorded separately. Existing runtime metadata changes only on its next normal restart.
