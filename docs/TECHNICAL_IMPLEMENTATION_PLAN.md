# MellowCodex: assisted development, safe self-updates, and APC project intelligence

Date: 2026-11-07  
Status: partially implemented development source; production activation is NOT established. See section 15 for the continuation audit.  
Audience: Codex implementing the next MellowCodex releases  
Primary source checkout inspected: `E:/AI/repos/local-agent-hub`  
Reusable product inspected: `E:/APC_CORE` and the newer GitHub archive at `E:/AI/audits/apc-github-2026-11-07-da47822/apc-main`  
Target computer: Windows, Intel i5-11400F, 32 GiB RAM, NVIDIA RTX 3050 with 8 GiB VRAM.

## 1. Decisions and intended result

Keep the existing MellowCodex application, task store, browser bridge, MCP gateway, tools and local model service. Extend them rather than replacing the application with another agent framework.

The user must be able to request a feature or repair in Hebrew through either ChatGPT connection or the local application. The system discovers the relevant code, prepares a change in an isolated candidate, runs meaningful tests, reports evidence, and, when the request includes activation, safely replaces the running version. It retains the same task and can recover after a failed update or a broken ChatGPT conversation.

Four decisions govern implementation:

1. **Online: let ChatGPT do the planning and review.** Give it direct, bounded repository intelligence tools. Do not run a second local planning agent merely to paraphrase ChatGPT. A validated patch can be applied and tested without any local LLM; otherwise a single local coding worker performs the bounded implementation.
2. **Offline: use one resident model for a whole coding phase by default.** Benchmark a single-model workflow before adopting a two-model workflow. An optional CPU-resident language planner is an experiment, not the default. Do not switch models on every tool call or every test failure.
3. **APC is a substantive source of reusable behavior.** Port its project graph, keywords/aliases, context obligations, evidence and verified-solution semantics into a small local Python service. Preserve useful metadata through an importer. Use established parsers and search libraries underneath, rather than porting the entire PHP platform.
4. **Separate the updater from the updated agent.** A small non-LLM supervisor owns releases, process identity, health checks and rollback. The agent edits a candidate release; it does not overwrite the executing installation or restart itself through arbitrary shell commands.

This is software self-development, not self-training of model weights. Better tools, context, prompts and tested repair memory can improve results without fine-tuning. No small model on this hardware is established as equivalent to Codex. The closest practical online workflow uses ChatGPT/Codex-quality reasoning plus local repository access and deterministic execution. Offline quality must be measured and reported separately.

## 2. Evidence and limitations of this audit

### 2.1 Observed local state

| Item | Observed evidence | Implication |
|---|---|---|
| Hub source/version | README, CHANGELOG and source identify 0.14.0; `GET /openapi.json` also reported 0.14.0 | Source and endpoint version labels agree in this observation; this is not a complete deployed-file hash comparison |
| Hub Git | This checkout has an unborn `master` branch, untracked source, and no remote returned by `git remote -v` | Establish a verified baseline before worktrees or rollback. Do not assume a browser-open GitHub repository is this checkout's upstream |
| APC Git | Local HEAD `b0535f43`, dated 2026-08-12; inspected status was clean | Local code is available regardless of whether every release was pushed or deployed |
| APC GitHub | Private `yodacoin/apc`, main commit `da4782284cff68e3310749583f6f0b26e0907d55`, dated 2026-08-23; README version `0.0.994-mellowyak-owner-resolution` | Newer source was downloaded through the authenticated internal browser and unpacked separately; use this snapshot for the reuse baseline |
| Model installed | `qwen3.5:4b`, Q4_K_M, 4.2B, 3,324,173,934 bytes; digest `d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04` | This is the measured installed artifact, not an assumption based on a mutable model tag |
| Model settings | `coding_model` empty; context 16,384; response 512; keep-alive 30 minutes; visual guidance false | A separate coding model is not currently selected. Do not silently turn feedback on during implementation |
| GPU during audit | Ollama `/api/ps` returned no models; NVIDIA reported 8192 MiB total and 629 MiB used | Models were already unloaded. The remaining memory is not evidence of a loaded LLM |
| Hardware | Previously collected local hardware report plus current GPU query | Recheck free RAM/VRAM before benchmarks; background applications change available capacity |

An existing local repository may have been published from another directory. Phase 0 must reconcile repository identity and preserve all local work; it must not blindly initialize a replacement history or force-push anything.

### 2.2 Verification performed in this audit

Command, run in `E:/AI/repos/local-agent-hub`:

```powershell
E:/AI/tools/hub-venv/Scripts/python.exe -m pytest tests/test_model_memory.py tests/test_model_context.py tests/test_extensions_documents.py -q -p no:cacheprovider
```

Result: **13 passed in 2.18 seconds**. These are fixture tests of memory controls, bounded context, extensions and documents. They are not proof of autonomous self-update, model coding quality, CPU performance, or browser/MCP end-to-end acceptance.

APC was audited by reading source, selected contracts, documentation and local Git metadata. Its full application, database and browser integration were not run. `composer.json` requires PHP `^8.3`; the inspected XAMPP CLI is PHP 8.0.30 and the inspected Laragon installation is older. Do not label APC tests as failed because an incompatible runtime was available; they were not executed in this audit.

The user clarified that some approval/publication markers remain unfinished because publication was not completed. A `PENDING` documentation label is therefore a **verification/publication boundary**, not evidence that a feature is missing or broken. Conversely, implementation in a local file is not proof of performance in this different product. Record these independently.

The downloaded archive is `C:/Users/MellowYak/Downloads/apc-main.zip`, 54,280,585 bytes, SHA-256 `0657154558f30f6743158dc4551e4d53aaeceabf32c323755158252c807326ae`. Its ZIP comment contains the full GitHub commit above, matching the visible repository head. Its 14,921 entries expand to 188,411,968 bytes. Archive paths and symlink entries were checked before extraction. No APC source, database, runtime, cloud deployment or original checkout was replaced. The archive and audit snapshot are useful source evidence, not disposable cleanup.

The newer snapshot adds source/work-location separation, paired-bridge command delivery and persistent direct-chat recovery behavior. Targeted comparison found identical text in `inc/project_map.php`, `api/project-map-search.php`, `inc/context/context_optimizer.php` and `inc/context/staged_play.php`. Newer application code was inspected, not executed. A global file comparison is recorded separately; identical core files do not imply that the entire repository is unchanged.

The archive contains 13,411 files. Comparing common paths with the older checkout found 1,362 byte differences: 1,278 disappear after UTF-8 BOM/CRLF normalization and 84 retain text changes. There are 33 archive paths absent from the older tracked inventory. Another 2,163 older tracked paths are absent from this archive; this is **not a deletion count**. `.gitattributes` explicitly excludes runtime state, project maps, evidence, backups and other paths from source archives. Do not treat those omissions as lost work or delete local evidence. Full machine-readable inventories are retained under `E:/AI/audits/apc-github-2026-11-07-da47822/`.

### 2.3 Existing Hub features to extend

All paths below are relative to `E:/AI/repos/local-agent-hub`.

| Existing implementation | What is reusable | Gap to address |
|---|---|---|
| `hub/store.py` | SQLite WAL tasks/events/actions, revisions, idempotency and unknown-action recovery | Add durable phase/worker/upgrade identities and bounded pagination without introducing another authoritative task database |
| `hub/conversations.py` | Persistent projects/chats and recent turn context | Add task packets and retrieval across older relevant history; a twelve-turn window is not full memory |
| `hub/model_context.py` | Compact JSON evidence without modifying audit history | Add code-specific tool catalogs, exact token accounting where supported, mandatory context and source references |
| `hub/model_memory.py` | Direct status/load/unload/switch APIs and verification | Add internal leases and phase handoffs; manual unload currently disables inference and is not an internal scheduler primitive |
| `hub/model_settings.py` | Installed-model selection and `coding_model` setting | Separate roles, residency policy and benchmark-selected profiles |
| `hub/tools.py`, `coding_ask` branch | Sends a question to `coding_model` or primary model | Returns advice, not executed code. It does not implement a complete coding-worker lifecycle or phase-level residency |
| `hub/extensions.py` | Versioned Python extensions, separate test, content hash, atomic manifest replacement | Isolate execution and strengthen independent tests; a generated test passing is not sufficient protection |
| `hub/engine.py` | Single task execution lock, tool loop and checkpoints | Add one-owner coding phases; current system instruction prohibits core modification, so core changes need a scoped update workflow |
| `hub/mcp_gateway.py` | Authenticated durable submission, status and file delivery | Add repository intelligence, revisioned guidance and release controls; verify advertised live tools, not just source decorators |
| `hub/chatgpt_bridge.py`, `hub/bridge_controller.py`, `hub/bridge_transcript.py` | Browser dialogue, message identity, uncertain-send recovery and saved transcript | Reuse for structured guidance/context requests, correlated to one human task; no second execution queue |
| `hub/adapters.py` | Optional OpenCode server adapter | Currently hardcodes Qwen in its prompt adapter. Not the default executor; do not activate a competing planner |
| `start.ps1`, `hub/admin_startup.py` | Startup, stale-version detection, active-task guard | They are not a transactional A/B updater. Avoid broad elevated execution as the ordinary development mode |

`start.ps1` already requests `OLLAMA_NUM_PARALLEL=1` and `OLLAMA_MAX_LOADED_MODELS=1`. The launch default is 8K, while the saved model settings request 16K explicitly. Confirm effective settings at runtime; changing a launcher environment does not reconfigure an existing Ollama process.

## 3. Execution modes and ownership

| Mode | Planner/reviewer | Local LLM | Repository access | Expected behavior |
|---|---|---|---|---|
| ChatGPT through MCP | ChatGPT | None for patch execution; one coder when needed | Shared repository tools through MCP | ChatGPT can inspect context, guide an existing task, inspect diff/tests and request an authorized update |
| ChatGPT through browser bridge | ChatGPT in the explicitly linked conversation | Same as MCP mode | Typed requests serviced by the same context service | Browser adapter transports requests/results; it does not become a second agent |
| Direct local, offline | Selected local model | One GPU model for the phase by default | Same context service in-process | No ChatGPT, remote embeddings, cloud inference or hidden downloads |
| Optional CPU planner + GPU coder | Small CPU-only planner, invoked sparingly | One GPU coder plus optional idle CPU-resident model | Same shared context | Enable only after comparative tests show value without harmful CPU/RAM contention |

The supervisor, scheduler, database, search index and tool runner are ordinary programs. They do not require their own LLM. Two processes or two release directories do not mean two loaded models.

### 3.1 Online path: make ChatGPT an informed director

1. Bind the human request, project, conversation and authorization scope to a durable task.
2. Obtain a small project overview and search results before asking for a plan. ChatGPT can then request exact symbols, relationships, source ranges or failed test output itself.
3. Accept either a structured plan for the coding worker or an explicit patch against known file hashes.
4. For a patch: validate its scope and base hashes, apply it to a candidate, and run tests without loading Qwen. Return the diff and evidence to ChatGPT.
5. For a plan: the selected coding model owns the entire bounded implementation phase. It uses retrieval, writes patches, runs tests and repairs them, without consulting another local model after every tool call.
6. Ask ChatGPT for help at meaningful boundaries: unresolved design ambiguity, a repeated failure, a risky migration, or final review. Release the GPU during a long external wait unless another admitted task immediately needs it.
7. Persist the review and its exact candidate hash. A review of an earlier patch does not approve later edits.

This solves the user's concern that ChatGPT cannot see local files: it receives **search and source tools**, not an unrestricted drive dump and not just a prose summary. OpenAI's MCP server documentation supports exposing controlled infrastructure tools; it does not mean ChatGPT automatically sees a local filesystem. [OpenAI MCP server documentation](https://developers.openai.com/plugins/build/mcp-server)

### 3.2 Browser and MCP feedback are distinct transports

Keep the browser listener as a compatibility route, using its existing message identifiers and explicit conversation binding. Add machine-readable envelopes generated by the bridge, so users continue speaking naturally. Only accept a complete response from the bound assistant turn after generation has finished. Reject stale task/epoch IDs and quoted examples. Preserve uncertain-send reconciliation rather than sending duplicate messages.

Browser responses can request `context.search`, `context.expand`, `code.patch`, `test.run` or `task.guide`. The bridge validates and routes these to the same service functions exposed by MCP. File/web content returned by those functions is evidence, never an instruction to change the authorized task.

MCP is normally driven by the calling client. A server cannot assume that it can summon a new ChatGPT turn at any time. Return a durable task ID, support bounded waits and status polling, and expose a guidance tool. Add sampling or task extensions only after capability negotiation and client acceptance testing. The MCP Tasks extension supports durable work and optional subscribed notifications; it is not a guarantee that ChatGPT will resume its reasoning automatically. [MCP Tasks](https://tasks.extensions.modelcontextprotocol.io/)

For ChatGPT-directed work that needs a review after the client disconnects, retain `waiting_guidance`. If the user has selected an offline fallback and the existing authorization covers continuation, the local executor can resume locally from the saved packet. Do not silently change authority, upload more code or claim a remote review occurred.

### 3.3 Offline and CPU options

Default: one capable local model reads Hebrew and codes. Compare that against a phase-level split before introducing another planner. If a coding specialist needs an English brief, preserve the original Hebrew verbatim and all literal names/paths/numbers, produce a structured brief once, then leave the coder in control until a milestone.

CPU-resident planning is feasible to evaluate, but CPU memory residency and CPU inference are different costs. A resident idle model consumes RAM; active generation competes with parsing, tests and builds. On a six-core CPU, two simultaneous inference jobs are not a free optimization. Prefer brief planning/review calls between test runs. Record end-to-end time and responsiveness.

If tested, put the CPU planner in a separately configured CPU-only runtime, without bypassing the central resource broker. Confirm actual GPU allocation is zero; do not infer it from a setting name. Pin the model, context and thread count. Start with a two-thread cap and low process priority as a benchmark hypothesis, not a universal recommendation. If a separate Ollama instance is used, allocate a verified free loopback port and disable its cloud/network routes. No duplicated model downloads are necessary when the backend safely shares read-only weight files.

Do not alternate planner/coder after every action. Use a task packet, a deterministic scheduler and milestone-level guidance. A new user correction revises the packet at a safe boundary; a generic status question must not trigger model loading.

## 4. Hardware-aware model and resource policy

### 4.1 Candidate selection, not an unmeasured ranking

| Candidate | Role in evaluation | Decision |
|---|---|---|
| Installed Qwen3.5 4B Q4_K_M | Single-model baseline; Hebrew intent and coding loop | Keep as initial baseline and fallback. It is already installed and avoids swaps |
| Qwen2.5-Coder 7B Instruct Q4_K_M | Dedicated bounded coding worker | First low-cost specialist comparison, not a claim that an older code-specific model beats newer general models |
| Qwen3.5 9B Q4_K_M | Single stronger model for both language and code | Conditional quality experiment. Tight VRAM headroom; only continue if measured residency/context fits comfortably |
| Qwen3-Coder 30B Q4_K_M | Optional slow offline quality experiment using RAM/partial offload | Not the interactive default. Its package is about 19 GB; 3.3B active parameters do not mean 3.3B resident weights |
| Existing 4B or smaller model on CPU | Optional Hebrew planning while GPU coder stays resident | Evaluate only after one-model and online-direct paths work. Smaller Hebrew quality remains unproven |

The official Ollama listings inspected show about 4.7 GB for the 7B coder and a 6.6 GB llama.cpp Q4_K_M artifact for Qwen3.5 9B. These are **artifact sizes, not peak VRAM requirements**. Runtime versions and alternative backends can expose different artifacts under the same tag. KV cache, runtime buffers, vision components and the Windows desktop add memory. Pin digests and measure. [7B coder](https://ollama.com/library/qwen2.5-coder:7b), [9B](https://ollama.com/library/qwen3.5:9b), [30B coder](https://ollama.com/library/qwen3-coder:30b)

Do not download all candidates automatically during implementation. Benchmark the installed model first; add one challenger at a time under the user's authorized installation scope. Keep its model license and source/hash record. Do not choose a model solely because the name contains “Coder.”

### 4.2 Residency, memory and latency

Implement a shared `ResourceBroker` and `ModelLease`:

- At most one GPU inference owner and one GPU model by default; external Ember jobs also count as resource users.
- One coding phase keeps its selected model resident through edits and tests, subject to a bounded idle lease. Do not unload after every request.
- Stop, task completion, long guidance wait and explicit unload release the task lease. Unload only models owned by this service; do not kill unrelated GPU programs.
- Manual unload remains a user preference that disables future automatic reload until explicitly re-enabled. Internal phase release does not alter that preference.
- Status/search/diff/test APIs must work with inference disabled.
- Use `/api/ps` and GPU telemetry to verify unloading. Check absence of the owned model, not zero total GPU memory. Escalate an unload timeout as an observable fault rather than immediately loading another large model.
- Preserve the current selected model if a switch fails; report whether it is unloaded, available for reload, or blocked. No ambiguous “switched” success.
- Across processes, use a durable lease plus process identity and fencing token. A Python `asyncio.Lock` alone cannot protect multiple workers/services.
- Queue for an active Ember voice/image/video workload. Do not force-stop it. If explicit Ember offload APIs exist, integrate them after inspecting their real contracts; otherwise report the busy owner.

Start code mode at **8K context**, a compact code-only tool catalog, and approximately **2K output**, increasing to 16K/4K only after measurement. A larger advertised context window does not make it affordable. Current global prompts and tool descriptions must be reduced by mode before expecting an 8K profile to work.

Use a configurable initial admission reserve of 1.25 GiB GPU headroom and 8 GiB system RAM headroom. These are proposed conservative operating limits, not measured peaks. Budget from predicted peak allocation plus an error margin; record actual peaks and adapt. Limit CPU index workers to one, and test/build concurrency to two initially. Pause background indexing if foreground latency or RAM pressure exceeds its budget.

Ollama's `keep_alive: 0` releases a model. Its model-count/parallel settings help control residency but do not arbitrate Ember or arbitrary external GPU processes. Keep a short bounded idle period inside a task and release at the task boundary. Verify behavior with the installed server version. [Ollama memory controls](https://docs.ollama.com/faq)

Do not enable speculative decoding with a second draft model by default. Do not make aggressive quantization, CPU offload or a large context a hidden fallback. If optional KV-cache quantization/Flash Attention is tested, record compatibility, correctness and memory results for the exact backend; leave it off if not established.

### 4.3 Benchmark gate

Create a reusable local benchmark, not a one-off demonstration. At least 24 small tasks should cover Python, JavaScript, PHP, PowerShell, Hebrew instructions, mixed RTL/LTR literals, multi-file edits, an intentional failing test, stale context, and recovery. Include representative MellowCodex/APC patterns in synthetic repositories; do not mutate production projects.

Compare: installed single-model baseline; dedicated coder with one prepared packet; online ChatGPT plan/patch path; optional CPU-planner path. For a 9B/30B candidate, first run an admission and one-task latency gate before the full suite. Run both cold and warm phases and repeat the hardest cases.

Measure task pass rate, first correct patch, repair count, peak VRAM/RAM, CPU time, load/unload time, prompt tokens, total wall time, Hebrew constraint fidelity and UI responsiveness. Count errors and timeouts. A model-swap experiment is useful only when its total quality/latency tradeoff beats staying on one model. Do not label it “optimal” from a tokens-per-second comparison.

Suggested selection rule: no regression in scope/data safety; at least baseline task success; adopt a specialist only for a clear measured quality improvement or material wall-time improvement. Report actual numbers and let slower quality mode remain optional. Cloud/Codex comparisons are separate and require an explicitly authorized account; do not call paid providers merely to populate a development benchmark.

## 5. APC reuse audit and extraction decisions

The model shortlist above is a benchmark starting point, not a restriction on models the user can install. The following model-management requirement was added by the user after the initial plan.

### Model catalog, automatic installation and natural-language selection

Deliver a first-class Models surface and equivalent chat operations. The user can browse/search downloadable models, choose one, have it downloaded and installed automatically, and select it for general tasks or coding. Support both the local application's chat and ChatGPT through MCP/browser feedback. Catalog lookup and installation orchestration must not depend on the model being downloaded or require a local LLM to be loaded.

**Shared user flow:** search -> choose model/variant -> resolve compatibility -> download -> verify/register -> select role -> load when needed. An explicit request such as “download this model and use it for coding” covers the whole compatible workflow; do not ask again at each step. Merely viewing a model or its card does not start a download. Download-only does not load the model into VRAM or change the selected model. If size/variant is unspecified, resolve a compatible suggested variant and show the resolved choice; ask only when a material ambiguity cannot be resolved from the user's settings and request.

**Sources:** implement provider adapters for Ollama Library and Hugging Face first, plus an extensible adapter interface for other repositories and direct model links. Search all available provider results with pagination, rather than maintaining a fixed hardcoded shortlist. Show source, publisher, exact model/variant, architecture, purpose, languages where documented, quantization, download size, license/access requirements, installed state and compatibility estimate. Unknown metadata remains unknown. Separate local downloadable models from cloud-only offerings. Use documented provider interfaces; do not invent an Ollama global catalog endpoint if the installed version has none. A cached provider catalog or documented provider-page adapter can supply discovery; exact model references must also work independently of search availability.

**Ollama adapter:** use the installed server's supported pull interface and progress stream; retain per-layer progress, errors and final manifest identity. Register the actual installed tag/digest and verify through model inspection before marking ready. A transfer finishing is not sufficient evidence of a usable model. [Ollama pull documentation](https://docs.ollama.com/api/pull)

**Hugging Face adapter:** resolve repository revision, required files and a compatible quantization before downloading. Prefer supported GGUF artifacts for the existing Ollama runtime. Hugging Face documents direct Ollama references for GGUF repositories and explicit variant selection; Ollama also supports local GGUF imports. Record the resolved artifact hashes/revision even when a provider tag is mutable. Download all required shards and architecture-specific companion files, not only the first matching file. [Hugging Face Ollama integration](https://huggingface.co/docs/hub/en/ollama), [Ollama model import](https://docs.ollama.com/import)

“Any model” means unrestricted discovery and selection of supported models, not a promise that every Hugging Face architecture runs in Ollama or fits 8 GiB VRAM. For incompatible artifacts, show the exact missing runtime/format requirement and a compatible alternative. A supported backend adapter may install its pinned runtime/dependencies automatically within the authorized scope. Do not execute arbitrary repository setup scripts or enable remote model code implicitly. Conversion/quantization is a separate bounded job with disk/RAM prerequisites; never pretend renaming a file makes it compatible. Private/gated models require the user's existing account access or a one-time login/license handoff. Keep tokens in protected credential storage, never chat text or logs.

**Hardware and lifecycle:** estimate disk space including temporary files, import/conversion overhead and shared caches; distinguish download size from runtime RAM/VRAM. Label fit as measured, estimated, CPU/partial-offload, or unsupported. Permit a deliberate download-only choice even if the model cannot currently fit in GPU memory. Loading still goes through ResourceBroker and must not evict an active task or launch multiple GPU models unexpectedly. Selection persists only after registration and capability validation; verify actual load separately and preserve a working fallback on failure. Models that generate text but lack the required tool interaction must not silently become an autonomous coding worker.

**Durable installation job:** persist provider, repo/tag, resolved revision, artifact set, bytes completed/total, phase, retry state and request ID. Phases include resolving, downloading, verifying, importing, validating, ready, failed and cancelled. Report byte progress where total size is known; otherwise show an indeterminate phase. Support cancellation and resume where the backend supports them, deduplicate repeated requests, handle interruptions/rate limits and keep valid shared blobs. Do not claim that cancelling an HTTP stream stopped a backend download until observed. Publish ready state atomically after verification; never select a partially downloaded model. An optional inference smoke test uses a resource lease and unloads afterward; if it cannot run, distinguish installed/compatible from runtime-tested.

**Shared operations:** add `model_catalog_search`, `model_catalog_details`, `model_install`, `model_install_status`, `model_install_cancel`, `model_install_resume`, `model_list_installed` and `model_select` through the same service to API, UI, MCP and browser envelopes. Names are proposed; publish actual schemas in capabilities. Support natural requests such as “show coding models suitable for my computer,” “download this Hugging Face model,” “resume the download,” and “use this model for coding.” Return resolved model IDs, job IDs, persisted role and effective activation status. Ordinary requests should not require JSON, shell commands or manual copying of model files.

**Implementation:** add a small `hub/models/` package with `catalog.py`, provider adapters, `installer.py` and `registry.py`; reuse existing task/event storage, settings and `model_memory.py`. The inspected memory controller currently accepts installed models only and explicitly does not download them, so retain that contract and call the new installer before selection. The registry records provenance, runtime, digest, role compatibility and measured resource profile. Use the Ollama/Hugging Face caches where appropriate rather than duplicating every weight file. Put controls and localized progress/error messages in the existing application, with full UI/chat parity.

**Delivery gate:** complete this feature before Phase 3 model comparisons. Synthetic provider fixtures cover pagination, incompatible formats, missing shards, gated access, low disk, corrupt downloads, interrupted streams, retry/cancel races and duplicate installs. Then exercise a real authorized download/registration/selection through the local agent and a fresh ChatGPT connection, and repeat selection through UI. Verify restart recovery, model role persistence, fallback on load failure and absence of unintended GPU residency. Do not download a large model merely to validate progress UI.

### 5.1 What is actually implemented

Paths and functions below were inspected in local source, including the downloaded newer snapshot. Use commit `da4782284cff68e3310749583f6f0b26e0907d55` for the extraction baseline and retain the older checkout for comparison. The table is a selective architectural audit, not a claim to have executed or reviewed every line of APC.

| APC subsystem/evidence | Value to MellowCodex | Implementation decision |
|---|---|---|
| `inc/project_map.php`: `apc_project_map_build_raw_search_index` | Indexes files, routes, pages, areas, elements, symbols, learned relations, manual overrides, behaviors, flows and states; raw terms include names, selectors, keywords and aliases | Preserve entity schema and retrieval behavior. Import existing metadata; implement local indexed storage rather than loading one large JSON document per query |
| Same file: `apc_project_map_extract_file` | File hashes, symbols, routes/imports/includes, evidence snippets and relation confidence | Reuse semantics and fixtures; replace regex-only language extraction with Python AST/Tree-sitter where appropriate. Keep heuristic edges explicitly heuristic |
| Same file: `apc_project_map_source_file_index_diff`, source inventory and refresh functions | Added/changed/deleted/unchanged detection and incremental source identity | Port directly at the algorithm/contract level into Python; retain no-op refresh behavior and deletion handling |
| Same file: `apc_project_map_build_url_file_graph` | Connects source/shared components to affected URLs | Port as one typed relation adapter; add Python/FastAPI routes for Hub |
| `api/project-map-search.php` | Target-aware keyword search, exact-identity boost, match reasons, related files and data hints | Preserve explainability, fields and target-first workflow; use FTS5/BM25 plus deterministic boosts. Current endpoint scans/sorts document candidates, so benchmark rather than assume large-repo speed |
| `inc/project_map.php`: context pack and enrichment functions | Bounded source context; labels, aliases, keywords, summary, behavior notes, limitations and confidence | Port schema and workflow. Fix global budgeting: cap the entire response, not just each snippet. Generate metadata only when useful; retain exact code separately |
| Same file: behavior/flow APIs and learning records | Expected behavior, `must_not_break`, user labels, keywords, aliases and resolved related files | First-class required feature, not a later cosmetic tag system |
| Same file: stable registry/manual overrides; `inc/project_map_living_manual_v2.php` | Stable target identity, operator corrections, feature grouping and provenance | Preserve human corrections across rescans. Do not conflate a guessed grouping with verified identity |
| `inc/context/obligation_compiler.php`, `task_contract.php` | Explicit identity/objective/targets/constraints/acceptance/current state/verification | High-priority port to typed task packets; these fields cannot be dropped by relevance scoring |
| `candidate_engine.php`, `candidate_sources.php`, `budget_optimizer.php`, `context_router.php` | Relevant candidate selection, cost/coverage tradeoff, diversity, safe payloads and bounded output | Extract a deterministic Python selector with fixture parity. Start simple; enable advanced ranking only after recall measurements |
| `context_ledger.php`, `model_sessions.php`, `session_delta_planner.php` | Versioned delivery scope and exact hash/session matching | Reuse identities and audit states. Do not infer model memory from an ACK; stateless inference still needs a complete working packet |
| `recall_classifier.php`, `reminder_engine.php`, `capability_cues.php`, `play_continuity.php` | HOT/WARM/COLD retrieval, reminders and task-specific capabilities | Retain the behavior with a smaller schema. HOT obligations and current task first; WARM repair history on demand; COLD archives as references |
| `inc/verified_capabilities.php` and solution-memory tests | Project/Area/Topic hierarchy, immutable versions, regression/supersession states, repair lineage | Port verified repair memory and immutable evidence. It must not auto-apply old patches to unrelated code |
| `inc/project_map_backup.php`, `project_map_runs.php`, `project_source_history.php` | Content identity, source history, snapshot provenance and resumable work | Use Git for code snapshots and SQLite backup API for live state. Import APC evidence references without replacing its backups |
| `inc/context/token_metrics.php` | Explicit distinction between estimated tokens and real provider usage | Preserve this honesty. Prefer exact model tokenizer; do not turn heuristic savings into measured claims |
| `semantic_variant_selector.php`, `semantic_codec_lab.php`, `omission_engine.php` | Experiments in compact representations and omission | Keep as optional shadow-mode research after baseline. Inspected selector explicitly uses SHADOW and `approved_for_delivery=false`; verify intended deployment separately, never silently enable lossy compression |
| `inc/screenshot_memory.php` and runtime/snapshot UI | Useful visual evidence linkage | Reuse explicit evidence fields, not filename-based project/viewport guesses as authoritative identity. Defer full screenshot gallery/browser clone |
| Newer `inc/project_connection.php`: source modes, work-location normalization, immutable revisions | Distinguishes local-only, Git-backed and externally managed source from development/build/test/runtime locations | Port the separation and bounded metadata. A recorded path/host is not permission to access or execute it. Keep location IDs and source snapshots in every task |
| Newer `inc/ops.php`: paired-bridge enqueue/claim/complete; `api/bridge-device.php` | Scoped command IDs, payload digests, duplicate handling, expiry and delivery receipts | Reuse protocol semantics with the Hub's transactional SQLite store, not another JSON queue. Add lease fencing, cancellation and uncertain-outcome reconciliation; delivery completion is not business-task acceptance |
| Newer `inc/direct_chat.php`, `sessions.php`, `tests/test_direct_chat_persistence_contract.py` | Durable conversation/task binding, prevention of old-thread telemetry contamination, bounded history, visible queues and reconnect | Port behavior and regression scenarios into existing Hub chat/bridge services. Use paginated history and explicit truncation; do not copy fixed oldest-message windows or a second chat application |

The investment is useful: APC contains concrete code for the features the user described, including keywords and aliases. The recommendation is **not to throw it away**. The recommendation is to transplant its domain model, metadata, selection logic and regression cases while replacing infrastructure that is inappropriate for a small local Python application.

### 5.2 What not to transplant wholesale

Do not add APC's full PHP/cloud/tenant/admin/database stack as a permanent dependency of MellowCodex. Do not duplicate authentication, task queues, browser runtimes or Git backup systems. Do not port the entire 413 KB `project_map.php` monolith merely to use five mapping functions. Do not add an always-running embedding LLM or graph database before basic lexical/symbol search is measured.

Aider's token-budgeted repository map is a useful comparison for ranking; Serena offers language-server symbol/reference tools. Prefer their established underlying approaches over inventing another parser. Neither replaces APC's user-authored behavior metadata, task constraints, provenance or recovery packet. [Aider repo map](https://aider.chat/docs/repomap.html), [Serena](https://github.com/oraios/serena)

Use SQLite FTS5 for local lexical search, Python AST for initial Python extraction, and pinned Tree-sitter grammars for JavaScript/TypeScript/PHP. Optional Serena/LSP adds stronger reference resolution later, only for active projects. This needs CPU/RAM, not another GPU model. [SQLite FTS5](https://sqlite.org/fts5.html), [Tree-sitter](https://tree-sitter.github.io/tree-sitter/)

### 5.3 Reuse process and proof

Create an `apc-reuse-manifest.json` listing source commit, source path/function, file SHA-256, destination module, behavior preserved, tests ported and deviations. Preserve attribution and review source/component license obligations before publishing extracted code; APC's composer manifest labels the product proprietary. Private reuse of the user's code does not authorize silently relicensing unrelated dependencies.

For pure algorithms, port test inputs and expected outputs, not just prose descriptions. If the PHP test runtime is installed for parity, use PHP 8.3 in an isolated test environment with a synthetic data root; never point migration tests at the real APC database. Where running the original is unavailable, label equivalence unverified until fixture parity or independent behavior tests establish it.

Import APC JSON metadata read-only through a versioned adapter. Bind imported IDs to their original project/source revision; revalidate file paths/hashes against the new project. Preserve manual tags and notes, mark stale references, and report imported/skipped/conflicting counts. No wholesale import of accounts, credentials, personal screenshots or unrelated chats. Leave original APC data intact.

### 5.4 Newer snapshot: precise additions and boundaries

`project_connection.php` defines `local_only`, `git_backed`, and `external_managed`, with independent development/build/runtime/test locations, canonical normalization and immutable connection revisions. Reuse this directly in the target design: the current source checkout, an isolated candidate, the testing environment and the active release are different locations belonging to the same project. Remote Git is optional for a local-only project; a recoverable source snapshot is still mandatory before mutation. The MellowYak registration feature itself is project-specific and is not needed in MellowCodex.

The paired-bridge queue bounds requests, associates them with project/device/connector identities, deduplicates matching active work and records `QUEUED`, `CLAIMED`, `COMPLETED`, `FAILED` or `EXPIRED`. Preserve those distinctions. Do not directly transplant its transport-specific trust shortcuts or conclude that a claimed-but-disconnected job is safe to replay. The new Python implementation must authenticate the exact endpoint, maintain a lease epoch, and reconcile side effects before retrying. A private IP range alone is not server identity.

Direct-chat code records conversation/message/task associations and rejects pre-claim snapshots from a previously focused thread. Its tests describe FIFO delivery, visible cancellation, reconnect, bounded busy retry, and no repaste after partial delivery. These are valuable acceptance scenarios for the current browser bridge. Transport text snapshots remain observations, not authoritative tests of a code change. Do not depend on APC's VS Code-specific command names or install its browser/IDE extension as a requirement.

The newer Workstream code also supports draft versus queued tasks, explicit edits and per-task execution/proof settings. Preserve this distinction in the shared work-packet service: saving a plan must not start execution, and changing guidance must increment a revision. Its legacy transport has an explicit operator-continue path for uncertain attempts. Reuse the idea of an audited continuation, but never generalize it into automatic replay of an action whose side effect is unknown.

The optional future APC integration can exchange project IDs, context references and task/evidence metadata through a scoped adapter. It must not become a hard dependency or require APC's cloud services, Docker, tenant database or another model on this computer.

## 6. Project intelligence available to every director and worker

### 6.1 Storage and identity

Keep authoritative tasks in the existing SQLite store. Use a separate rebuildable `context.sqlite3` for large source indexes so indexing cannot lock task control. Store human-authored annotations and verified repair records durably in the main state store or a separately backed-up authoritative store; they must survive index rebuilds.

Minimal entities:

```text
Project(project_id, canonical_root, repo_identity, source_mode, policy_revision)
WorkLocation(location_id, project_id, role, platform, registered_root, status, policy_ref)
ConnectionRevision(id, project_id, source_location_id, runtime_location_id, revision)
SourceSnapshot(snapshot_id, project_id, worktree_id, base_commit, dirty_manifest_hash)
File(file_id, snapshot_id, relpath, content_hash, language, size, encoding)
Symbol(symbol_id, file_id, qualified_name, kind, range, extractor_version)
Feature(feature_id, project_id, title, description, area, expected_behavior)
Alias(alias_id, entity_id, language, text, author_kind, source_ref, confidence)
Tag(tag_id, entity_id, text, language, provenance)
Relation(edge_id, from_id, to_id, kind, evidence_ref, confidence, snapshot_id)
Annotation(id, project_id, entity_id, must_not_break, notes, revision)
Evidence(id, task_id, artifact_hash, source_snapshot, test_command, result, timestamp)
RepairMemory(id, project_id, area, topic, symptom, fix_summary, evidence_ids, status)
ContextDelivery(id, task_id, consumer_epoch, packet_hash, source_snapshot, transport_state)
```

Keep stable entity IDs separate from content versions. A rename can preserve file identity when Git or explicit evidence supports it; ambiguous renames require reconciliation. Ranges are valid only for their content hash. A relation may be `imports`, `defines`, `references`, `serves_route`, `renders`, `calls_api`, `reads_setting`, `tested_by`, `affects`, or `explains`. Unsupported edges remain unknown, not invented.

### 6.2 Incremental scan

1. Discover the explicitly selected project root and its rules. Resolve Windows junctions/symlinks and enforce an allowed-root boundary.
2. Use Git's tracked-file inventory plus explicitly allowed untracked source. Exclude secrets, dependency trees, models, media, state DBs, generated caches and build output. For non-Git projects use a bounded manifest scan.
3. Hash changed files, parse only the affected files, update reverse edges and invalidate dependent snippets. Rehash immediately before applying a patch; mtime/size alone are not a write precondition.
4. Watch edits with debouncing; reconcile watcher loss on startup or on-demand refresh. Searches return index revision, freshness and omitted coverage.
5. Never require a full repository rescan for a status question or a new chat. Full indexing is a resumable low-priority job, with byte/file/time limits and cancellation.
6. Scope caches by project AND worktree snapshot. Candidate code must not contaminate the live project's index.

### 6.3 Keywords, tags, aliases and multilingual retrieval

Search exact paths/symbols/IDs first, then FTS5 over labels, descriptions, aliases, tags, behavior notes, test names and source text, then bounded relation expansion. Return why each result matched.

Preserve Hebrew, Russian and English. Maintain separate normalized search text; never rewrite literal source identifiers or filenames. Support Unicode normalization and optional Hebrew diacritic-insensitive lookup in the search field only. Technical labels can have curated aliases in all three languages. A user statement such as “this is the model switching screen” becomes an explicit annotation linked to an observed entity.

LLM-generated keywords are optional derived metadata with source hash, language, provenance and confidence. They must not overwrite user annotations or verified source facts. Generate them lazily for important entities using the active director or idle model; do not run a new background LLM to describe every file. A stale generated summary is invalidated when its source changes.

Without embeddings, Hebrew-to-English concept search depends on aliases and query expansion. Measure misses honestly. Only add a compact CPU embedding model if a multilingual retrieval evaluation demonstrates a worthwhile improvement; version the embeddings and keep exact identifier search first. No vector database or GPU embedding service is required for the first release.

### 6.4 Progressive source access

Expose a project overview with entry points, components, dependencies, known tests, conventions, active task and current source revision. Search returns a short list of handles, snippets, tags, relationships and freshness. `context_expand` retrieves exact bounded line/symbol ranges. `context_related` expands one or two graph hops under an edge/result budget. `context_pack` combines the chosen material with required task obligations.

ChatGPT must be able to follow these references without asking the local LLM to explain each file. In MCP mode they are real read-only tools. In browser mode typed context requests are served by the bridge; provide a downloadable plain-text packet/manual handoff if that client cannot exchange structured requests. No arbitrary host paths may be supplied remotely.

Example interaction, with IDs supplied by real tool results:

```text
Human: Improve your model switching without changing my voice engines.
Director -> project_context: identify selected repo, constraints, current snapshot.
Director -> context_search: queries for switching, coding_model, unload, Hebrew aliases.
Director -> context_related: callers, configuration persistence, existing tests.
Director -> context_expand: exact source ranges and their hashes.
Director -> submit_task: scoped change packet and acceptance checks.
Worker -> tests/diff -> Director review -> authorized activation.
```

### 6.5 Context budgets and memory truth

Pin the human goal, original language, constraints, scope, acceptance checks and unresolved action outcomes. Rank optional material by relevance, freshness, dependency distance, evidence quality and cost. Keep important source fragments exact; use summaries for orientation, not patch generation against unseen code.

For an 8K profile, a starting budget is roughly: 1K rules/tools, 1K task packet, 3K code/evidence, 1K recent tool exchanges, 2K output. These are tuning targets. Count the actual model template and system prompt; if they exceed the budget, reduce catalog/instruction duplication before dropping task constraints. If mandatory context still cannot fit, split the task or report the limit.

APC-style BOOT/DELTA is useful for transport and durable storage. It does **not** make a stateless Ollama chat call remember omitted earlier text. Reconstruct a sufficient packet for every inference. Model unload, model switch, new ChatGPT conversation, compaction or changed template invalidates assumptions about retained context. An acknowledged packet means received/parsed according to the recorded transport—not proven internal understanding.

## 7. Contracts, APIs and shared configuration

### 7.1 Work packet

Validate a versioned Pydantic/JSON Schema contract. Example shape (placeholders are illustrative, not existing IDs):

```json
{
  "schema_version": "mellow.work.v1",
  "task_id": "observed-task-id",
  "project_id": "observed-project-id",
  "base_snapshot": "observed-snapshot-id",
  "revision": 1,
  "human_request_original": "verbatim user request",
  "source_language": "he",
  "implementation_brief": "concise technical brief",
  "literal_values": [{"name": "identifier", "value": "preserved exactly"}],
  "constraints": ["preserve existing public tool names"],
  "allowed_paths": ["hub/", "tests/"],
  "excluded_paths": ["state/", "credentials/"],
  "acceptance": [{"id": "A1", "description": "expected behavior", "test_ref": "test handle"}],
  "context_refs": ["observed-context-ref"],
  "execution_profile": "assisted_code",
  "authorization_ref": "human-scope-record",
  "activation_policy": "within_existing_authorization"
}
```

Authorization comes from the authenticated human request/session policy, not from text inserted by a retrieved file or from a model setting its own permissions. Natural-language requests should be converted by the director into this contract and validated server-side. Show a plain-language summary in the user's language; do not force users to author JSON.

Guidance records include task ID, expected revision, consumer epoch, referenced evidence and guidance text/patch. Reject stale guidance with a conflict and the current revision. Patch proposals include base file hashes, candidate hash, affected paths, test plan and author. Support chunked artifact upload for large diffs, with digest and size limits, rather than huge inline MCP results.

### 7.2 Public operations

Extend the existing API and MCP facade. Names below are proposed; maintain compatibility with existing tools and publish actual available names in capabilities.

| Operation | Purpose | Inference required? |
|---|---|---|
| `project_context` | Overview, instructions, source/index version, capabilities | No |
| `context_search` | Keyword/tag/alias/symbol search with filters and pagination | No |
| `context_related` | Bounded dependency/feature/test relationships | No |
| `context_expand` | Exact versioned source snippets or archived evidence | No |
| `context_refresh` | Queue/resume incremental indexing | No |
| `context_annotate` | Save user labels, keywords, behavior and constraints | No |
| `submit_task` | Existing durable admission, optional work-packet reference | Only if profile needs it |
| `task_guide` | Revise/direct an existing task with expected revision | No for admission |
| `get_task`, `wait_task`, `get_events` | Actual state, events, blocker, results | No |
| `get_diff`, `get_test_results` | Review candidate and immutable verification evidence | No |
| `propose_patch` | Stage director-authored patch against exact base | No |
| `development_settings` | Read/change profiles, budgets, feedback and activation policy | No |
| `upgrade_status`, `upgrade_activate`, `upgrade_rollback` | Supervisor-mediated release operations | No |
| `recovery_context` | Resume packet for a fresh chat, including task/repo IDs | No |

All paths use the same service-layer functions and validation as the UI. Return saved setting values, revision, effective values, and `active`/`requires_restart`/`blocked` status. Add tool metadata and refresh capability catalogs; a tool in source that ChatGPT cannot discover is not delivered functionality.

Expose modes such as assisted/offline/quality and their tradeoffs in UI and natural-language MCP settings. Every new setting must be changeable through chat. Keep language catalogs and error keys central; if shared Ember files are touched, obey its matching Hebrew/Russian catalog rules. Do not introduce new hardcoded model-contract text throughout Python/JS.

The focused Hub file inventory did not identify a locale/i18n module by filename. Confirm whether a shared translator exists before implementing these surfaces. If none exists, introduce a small catalog loader and matching Hebrew/Russian catalogs for the new messages (plus English where the Hub requires it). Keep user-authored content and protocol IDs as data, not translated keys. Do not silently assume Ember's catalogs are already imported into this independent application.

### 7.3 Task and event state

Keep existing top-level task states compatible; add a `phase` and an orthogonal wait reason. Suggested phases: `context`, `planning`, `patching`, `testing`, `review`, `staging`, `activation`, `postcheck`. Reasons include `guidance`, `gpu`, `authorization`, `unknown_action`, `dependency` and `restart_recovery`.

Persist task transitions and events before acknowledging the client. Use monotonic event sequence IDs and replay cursors; retain paginated history beyond the current recent-task window. Persist `owner_id`, lease epoch, last heartbeat and retry count. SQLite is authoritative; checkpoint files remain projections.

UI uses SSE/WebSocket or bounded long-polling for live updates, reconnecting from its cursor. MCP can return progress during a live call and task handles where supported, but keep `get_task` as a working fallback. Do not implement fictitious percentages: use measured completed units or a named phase with elapsed time.

Review outcomes, test outcomes and activation outcomes are distinct. `waiting_review` and “patch written” are not success. A repaired candidate may be complete as a development artifact while activation remains explicitly pending; report both.

## 8. Safe development of the running agent

### 8.1 Process and ownership boundaries

Use four logical components, implemented with as few resident processes as practical:

1. **Control plane:** durable task admission, status/events, context access, settings and the existing MCP facade. It remains reachable while the coding worker is replaced.
2. **Worker:** the active agent release, with a scoped tool runner and optional leased model. A worker may create/test a candidate but cannot declare its own activation successful.
3. **Candidate runner:** short-lived test processes using candidate code, isolated data and distinct ports. It never connects to production chat queues or executes real desktop/media jobs during a smoke test.
4. **Guardian:** a small deterministic launcher/updater with its own journal. It checks manifests, drains the worker, activates a release, checks health and restores the prior release when necessary. It contains no model and does not continuously analyze code.

Start with the existing Hub/API process as control plane and a new isolated coding worker subprocess. Keep the public MCP gateway stable. Move restart-sensitive orchestration behind an adapter rather than rewriting every existing task tool. Agent-owned source changes may touch worker/application code within the authorized scope. A change to the guardian, control-plane protocol or security boundary is a separate staged update, not part of the ordinary worker self-update loop.

Suggested Windows layout, subject to Phase 0 identity reconciliation:

```text
E:/AI/repos/local-agent-hub/             authoritative development checkout
E:/AI/worktrees/<task-id>/               Git candidate, when Git is available
E:/AI/candidates/<task-id>/              manifest candidate for local-only source
E:/AI/releases/<release-id>/            immutable tested runtime code + environment
E:/AI/state/                            durable user settings/tasks; outside releases
E:/AI/state/upgrades/<upgrade-id>.json   guardian journal and recovery decision
E:/AI/artifacts/<task-id>/               diffs, tests, source manifests, evidence
E:/AI/backups/<upgrade-id>/              verified state backup and old release manifest
E:/AI/guardian/                         separately maintained launcher/updater
```

Do not assume these proposed directories already exist. Resolve their absolute paths, enforce expected roots and inspect existing content before creating or moving anything. Do not relocate the current installation as the first implementation step.

### 8.2 Candidate creation and patch application

- Freeze a base identity: Git commit plus permitted dirty/untracked changes, or a hashed local-only source manifest. Include dependency locks and relevant instructions.
- Preserve the user's dirty checkout. Prefer a task-specific Git worktree after repository identity is reconciled; do not use `reset --hard`, overwrite user files or force-push. For a local-only project, create a bounded candidate from an explicit source manifest without copying credentials, models or runtime databases.
- Candidate writes must stay inside the resolved candidate root. Validate relative paths, Windows drive/UNC paths, alternate data streams, reserved device names and junction/symlink escapes. Resolve again at the point of access to reduce time-of-check/time-of-use races.
- Require base hashes for modified files. Reject stale patches with the current source identity. Apply a multi-file patch as a staged set; retain the previous candidate if any part fails.
- Execute commands through an argument-vector process runner with explicit working directory, timeout, environment allowlist, output cap, exit code and cancellation. Do not concatenate model text into a shell command.
- Only project-authorized builds/tests are available to the coding worker. Import/build scripts can execute code; a folder allowlist alone cannot sandbox them.
- A failed test enters a bounded repair loop. Begin with at most three repair iterations per unchanged failure signature; then request director guidance or report the precise offline blocker. A user-directed continuation can raise the budget. Never delete failing tests or weaken acceptance to manufacture success.

Git worktrees isolate working files, not operating-system privileges. They share repository metadata and are not a security sandbox. [Git worktree documentation](https://git-scm.com/docs/git-worktree)

### 8.3 Actual test isolation on this computer

Make isolation an explicit execution profile, not a misleading “sandbox” label:

| Profile | Boundary | Use |
|---|---|---|
| Candidate workspace | Scoped file tools and separate test data; same Windows account | Trusted repository changes and fast deterministic checks; not protection against arbitrary code |
| Restricted test runner | Separate non-admin identity/token, process-tree ownership, restricted environment/ACLs, explicit network policy | Integration execution after that boundary is implemented and tested |
| Disposable Windows Sandbox/VM | OS boundary, no GPU, no production credentials, network disabled, bounded shared directories | Untrusted dependency/test execution or changes that require stronger isolation |

Feature-detect Windows edition, virtualization availability and free memory. Windows Sandbox is optional; do not claim it is installed or enable Hyper-V/WSL/Docker silently. On this hardware, keep it off when not needed. If used, the LLM stays on the host and produces a patch; the guest only runs tests, so a second model is unnecessary. Start with a 4 GiB guest budget only if the test workload and host reserve allow it; increase or reject admission based on measurement.

Windows Sandbox supports configuration of networking, vGPU, clipboard and mapped folders. Set these explicitly, use a read-only input mount and a dedicated writable output directory containing no secrets, and verify the actual boundary. Its default network access must not be mistaken for offline isolation. [Windows Sandbox configuration](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file)

If the required isolation backend is unavailable, return a clear capability result. Do not silently downgrade untrusted execution to the host. Conversely, routine authorized edits and trusted tests should not generate repeated permission prompts merely because a stronger optional backend exists.

### 8.4 Transactional activation and rollback

The normal update unit is an immutable release with a manifest containing release ID, source snapshot, file/dependency digests, schema compatibility range, required configuration, test evidence references and review/authorization references. Hashes establish identity and integrity; they do not prove the code is trustworthy.

Activation sequence:

1. **Prepare:** build the candidate's own environment; verify files and tests; smoke-test on an allocated private port with synthetic/copied test state. Keep production side effects disabled.
2. **Authorize from existing scope:** determine whether the human requested activation or only preparation. An existing authorized “implement and activate” request covers normal reversible activation. If approval is still needed, present the complete diff, test results and rollback plan now, as the final decision.
3. **Drain:** stop admitting new worker mutations, preserve queued tasks, and checkpoint current work. Do not terminate unrelated active work. An unknown desktop/network side effect must be reconciled or remain a recorded blocker.
4. **Backup:** use SQLite's backup mechanism or a quiesced consistent snapshot, verify integrity and SHA-256, and capture relevant non-secret configuration. Keep the active release immutable and available.
5. **Journal:** persist `PREPARED -> DRAINED -> BACKUP_VERIFIED` with old/new release IDs and an activation nonce. The guardian can recover even if the main task database cannot open.
6. **Migrate:** run only compatible, idempotent migrations through a designated writer. Ordinary self-updates use additive/expand-contract schema changes. Destructive migrations require a separate recovery design; a generic old-code rollback is not sufficient.
7. **Switch:** start the candidate, verify its release hash/nonce and readiness, then change the active worker pointer/routing under a lock using an atomic same-volume file replacement. Do not overwrite loaded DLLs or the running interpreter. Windows junction replacement is not assumed atomic.
8. **Observe:** run the acceptance probe through the real control plane. Confirm one active mutation owner, the selected release, state/schema compatibility, tool availability and a synthetic no-side-effect task. Use a bounded stabilization window, initially 60 seconds.
9. **Commit:** write `ACTIVE_VERIFIED`, retain the previous release/backup, release the drain and rebind the original task to the new worker epoch. Report the actual version and evidence.
10. **Rollback on failure:** stop only candidate-owned processes, restore the old routing and compatible worker, reconcile task leases and run the same health probe. Mark the update failed/rolled back even if the old application is healthy.

Before admitting production writes on the new release, old code must be able to read the migrated schema. If that cannot be guaranteed, remain quiesced until acceptance or use an explicit data-restoration workflow. Never restore an old database over new user work accepted after activation. Prefer a forward repair or a compatibility-preserving rollback; keep a write journal if a release's migration plan requires replay.

Crash recovery must cover every journal boundary, including power loss after switching but before recording success. On boot, the guardian determines the actual process/release identity and reconciles it with the journal; it does not infer success from a PID file. Use PID plus creation time/executable identity to avoid terminating a reused PID.

The guardian itself updates through a small independent bootstrap/maintenance path with separate verification. A worker cannot rewrite its own activation policy or guardian executable and immediately authorize the result. This is a concrete process boundary, not a promise that arbitrary self-modification is safe.

### 8.5 Learning from completed work

After verified completion, store the symptom, cause, affected symbols/features, exact source versions, successful tests, remaining limits and a short reusable rule in repair memory. A human correction may add a note immediately, but it is not automatically promoted to a verified general rule. If later evidence contradicts it, record a regression/superseding version.

At the next task, retrieve relevant repair records with their provenance. Recheck their preconditions against the current source. Do not auto-apply old diffs, silently modify global prompts, run endless self-improvement jobs, or train weights in the background. The user can explicitly request a bounded improvement session and select its time/iteration/resource budget.

## 9. Concrete implementation map

The following are proposed modules in `E:/AI/repos/local-agent-hub`; inspect the current tree before creating them and consolidate if equivalent modules already exist.

| Module or existing surface | Responsibility | Primary dependencies |
|---|---|---|
| `hub/development/contracts.py` | WorkPacket, Guidance, PatchProposal, ReleaseManifest, revision rules | Existing Pydantic |
| `hub/development/service.py` | Task admission, scoped orchestration, state transitions | Existing store/engine/conversations |
| `hub/development/workspaces.py` | Git/local-only snapshot, candidate creation, base hashes, diff | Git CLI, pathlib; no shell interpolation |
| `hub/development/runner.py` | Bounded subprocess execution, cancellation, test evidence | subprocess/asyncio, existing psutil |
| `hub/development/patches.py` | Validate/stage multi-file changes, path and conflict checks | Workspace service |
| `hub/context/store.py` | Separate FTS5 index and source versions | stdlib sqlite3 |
| `hub/context/scanner.py` | Incremental inventory, bounded reads, hash/invalidation | Existing file tools, optional watcher |
| `hub/context/extractors/` | Python AST; JS/TS/PHP Tree-sitter; heuristic adapters | ast, pinned compatible grammar packages |
| `hub/context/search.py` | Keywords, multilingual aliases/tags, filters, match reasons | FTS5, relation queries |
| `hub/context/packets.py` | Obligations, global token budget, exact source expansion | Contracts, model tokenizer adapter |
| `hub/context/apc_import.py` | Read-only versioned APC metadata importer | Source manifest and scoped paths |
| `hub/context/repair_memory.py` | Immutable evidence-backed repair retrieval | Authoritative state store |
| `hub/resources.py` | Durable model/GPU leases, admission, external load observation | Existing model_memory and telemetry |
| `hub/guardian/` or separately packaged guardian | Activation journal, launcher, rollback, release health | No LLM, minimal dependencies |
| Existing `hub/tools.py` | Mode-specific coding/context tools and compatibility | Shared services |
| Existing `hub/engine.py` | Dispatch coding mode, checkpoints and bounded repair loop | Development service, resource broker |
| Existing `hub/model_memory.py` | Separate user disable/unload from internal lease release | Resource broker integration |
| Existing `hub/bridge_controller.py` | Typed envelopes, exact conversation/turn correlation | Existing durable bridge and context tools |
| Existing `hub/mcp_gateway.py` and API routes | Public schema/auth/capabilities; no duplicate business logic | Shared service layer |
| Existing UI/settings/locales | Development mode, source map/search, diff/tests, updates, queue | Same persisted configuration |
| `tools/bench_development.py`, `tests/development/`, `tests/context/` | Reusable benchmark and regression suite | Synthetic fixtures, existing pytest |
| `docs/apc-reuse-manifest.json`, `VALIDATION.md` | Provenance, measured results, implementation limits | Source hashes and evidence |

Do not introduce a large agent framework merely for orchestration. Use the existing OpenCode adapter behind the same contracts if its actual patch/test loop is better than a small native worker; first remove its hardcoded model selection and connect resource leases. It must not launch an unmanaged second Ollama/model process. Keep one canonical worker path enabled per task. [OpenCode server API](https://opencode.ai/docs/server/)

An optional Codex-backed online worker can use a documented Codex integration when the user chooses it. Keep it separate from local offline inference and account access; do not equate a ChatGPT browser login with an API credential or an entitlement to unattended cloud jobs. The Codex app-server/SDK are integration surfaces, not downloadable Codex model weights. [Codex platform integration](https://developers.openai.com/blog/codex-as-a-platform)

Dependency policy: retain current pinned versions unless a feature requires a change. Add only one parser/watch/runtime dependency at a time, pin compatible versions and hashes, and test installation in the candidate. Standard-library AST, SQLite and Git should cover the first useful release. Do not install Docker, a graph database, a vector server or a second inference server as baseline requirements.

### 9.1 Shared execution loop

```text
admit(request, project, request_id):
    resolve authenticated scope and existing task identity
    return prior task if this request_id already exists
    persist original request + source revision + acceptance constraints
    choose explicit execution profile
    queue task and return task_id immediately

run(task):
    acquire task ownership with lease epoch
    build bounded context packet from deterministic search
    if director supplied a valid patch:
        stage patch; run verification without loading an LLM
    else:
        acquire one resource/model lease for the coding phase
        repeat edit -> test -> inspect evidence within repair budget
    checkpoint candidate hash, diff, tests and unresolved issues
    obtain review at a meaningful boundary, using the selected director
    if activation is authorized and checks pass:
        hand immutable manifest to guardian
        await observed active-release verification
    save repair memory only for claims supported by evidence
    release owned resources; verify model unload when task ends

on_interrupt_or_restart(task):
    fence the old worker; preserve task and action ledger
    reconcile any action that began but has no confirmed result
    resume only replay-safe steps from persisted state
```

Neither a new chat nor a reconnect creates a new implementation task unless the user requests one. Use task revision and consumer epoch to distinguish continued work from duplicate requests.

## 10. Implementation phases and completion gates

Do the work in this order. Each phase is independently reviewable and must leave normal existing operation usable. Do not begin by downloading every model or rebuilding APC.

### Phase 0 — Establish a recoverable baseline

1. Re-read current target rules, README, CHANGELOG, VERSION/packaging version and actual active processes.
2. Reconcile Hub source identity, remote and dirty/untracked content. The audited checkout has no first commit. Locate the intended existing upstream before creating history; if it is genuinely local-only, use a manifest baseline and a reviewed exact file allowlist for any initial commit.
3. Copy/hash current source/configuration and back up state consistently. Keep credentials out of the source manifest/export.
4. Record hardware, Ollama version/digest, model settings, installed capabilities and current model residency. Use a restore point for settings changed by benchmarks.
5. Preserve the downloaded APC archive. Generate the reuse manifest from its pinned commit and selected source files. Distinguish archive omissions/line-ending differences from source changes.

Gate: restore drill on a disposable copy succeeds; current behavior/tests have a recorded baseline; no live data or user edits are lost. No model download required.

### Phase 1 — Useful project intelligence without an LLM

1. Implement project/location/source identity, bounded inventory, file hashes and Python extraction.
2. Add FTS5 keyword search, tags, multilingual aliases, behavior notes, constraints and typed relations.
3. Port the selected APC retrieval/context invariants and read-only metadata importer.
4. Add overview/search/related/expand/refresh/annotate to the real API, UI and MCP tool catalog.
5. Add versioned exact source handles and a recovery packet for a fresh conversation.

Gate: a fresh connected ChatGPT conversation can independently locate and read the actual relevant source through these tools, with all local models unloaded. Hebrew/Russian/English retrieval fixtures and stale-file tests pass. An index rebuild preserves user-authored annotations.

### Phase 2 — ChatGPT-directed candidate development

1. Implement work packets, guidance revisions, scoped candidate patches, diff retrieval and test runner.
2. Make the online patch path work with no local model. A director-authored patch goes through exactly the same validation/test path as a local model patch.
3. Add a coding-worker phase to the existing engine, using one selected model and mode-specific instructions/tools when a plan requires local implementation.
4. Connect MCP guidance and the existing browser bridge to the same contracts. Add complete-turn detection, epoch binding, unknown-send reconciliation and visible queue cancellation.
5. Expose review evidence and accurate task status; do not activate self-updates in this phase.

Gate: the local agent's task runner completes a synthetic multi-file repair directed from a fresh ChatGPT chat through each transport. A broken test is repaired through the agent, not manually by the implementation assistant. Disconnect/reconnect does not duplicate edits or messages. Browsing uses the user's internal-browser preference; manual login remains a user handoff if needed.

### Phase 3 — Offline quality and resource selection

Prerequisite: deliver the Models catalog/install/select workflow above, including UI and natural-language chat parity. Use that workflow for model comparisons instead of one-off shell downloads.

1. Run the installed-model benchmark at the bounded context/output profiles.
2. Add one coder challenger, compare quality and total latency, then adopt or reject it with evidence.
3. Evaluate 9B only if admission fits; retain 30B partial offload as an optional slow experiment.
4. Add CPU planning only if the measured one-model/offline failure pattern justifies it. Test idle residency and active CPU contention separately.
5. Implement model leases, external GPU workload detection and end-of-task unload verification. Persist the tested profile, not merely a friendly model name.

Gate: fully offline synthetic repair passes with no network dependency; a Hebrew instruction preserves literal filenames/numbers and its constraints; no frequent per-action model swaps; final owned model is unloaded. Report remaining quality limits and benchmark data honestly.

### Phase 4 — Self-update foundation

1. Separate replaceable worker lifecycle from stable task/control access.
2. Implement immutable release staging, guardian journal, drain, backup, compatibility checks, activation and rollback.
3. Add restricted test execution as appropriate; do not advertise OS isolation until verified.
4. Run crash-injection tests at each activation boundary, including database migration failures and a locked Windows executable.
5. Verify that UI and ChatGPT can still retrieve task/update status during worker replacement.

Gate: the agent creates a benign change to its own candidate, tests it, activates it within the authorized scope, and completes the same task on the new worker. A deliberately unhealthy candidate rolls back without losing accepted tasks or corrupting state. Updating the guardian itself remains a separate tested procedure.

### Phase 5 — Product completion and release

1. Provide project-map search, task progress, diff/test evidence, settings and update/rollback views in the existing interface.
2. Verify every configurable feature through natural-language MCP requests and UI read-back, including the effective model and feedback mode.
3. Add verified repair memory, conflict/regression handling and fresh-chat recovery.
4. Record reuse attribution, source hashes, actual validation and known limits. Update Hub README/CHANGELOG/VALIDATION and synchronized package versions according to its rules.
5. Commit an exact reviewed file set. Follow the target project's release/deployment process; do not run Ember's publisher for an unrelated Hub release.

Gate: all required acceptance paths below pass. Keep separate statuses for implemented, fixture-tested, model-tested and real-client verified. Release notes must not describe future phases as already working.

## 11. Acceptance and failure-injection matrix

Tests should establish behavior and recovery, not merely assert that a function name appears in source. Use fixtures first, then real local-agent/ChatGPT acceptance for the relevant paths.

| Area | Required scenario | Observable pass condition |
|---|---|---|
| Retrieval | Hebrew request with an English technical identifier; Russian alias; misspelled human label | Relevant source appears in bounded results with match reasons; exact identifiers remain intact |
| Relations | UI setting -> API -> persistence -> tests across files | Correct observed edges and source ranges; guessed relationships labeled as such |
| Incremental index | Modify, delete, rename a file and change parser version | Only necessary items reindex; removed content is not returned as current; annotations survive |
| Source freshness | Patch/source expansion against a changed hash | Conflict returned; no silent patch against another revision |
| Context limits | Very large file, log and diff; oversized required constraints | Bounded output with continuation handles; required constraints preserved or explicit capacity failure |
| Import | Same APC metadata imported twice; stale path; conflicting annotation | Stable IDs/deduplication, explicit conflicts and original data preserved |
| Project isolation | Two repositories with identical filenames and aliases | No cross-project source, task or evidence leakage |
| Injection resistance | Source comment asks to exfiltrate credentials or disable validation | Treated as untrusted source data; scope and policies unchanged |
| Online direct patch | Local inference disabled; ChatGPT supplies a bounded patch | Patch/test/review completes without a model load |
| Coding loop | Synthetic bug needs coordinated edits and one test-driven retry | Agent-owned actions create correct patch and real test result; no manual business-task substitution |
| Hebrew fidelity | Negation, numbers, mixed Hebrew/English names and path punctuation | Original intent and literal values preserved; unexplained constraint changes fail acceptance |
| Offline | Network disabled after dependencies/models are installed | Local coding/retrieval/recovery works; no hidden cloud/API fallback |
| GPU contention | Existing Ember GPU job or another lease is active | Task queues or reports resource wait; does not stop the unrelated job |
| Model switch | OOM or load timeout after previous model was released | Accurate effective state, no second heavy load, baseline remains recoverable |
| End-of-task release | Success, failure, cancellation and long guidance wait | Owned lease released; `/api/ps` confirms intended unload; user disable preference preserved |
| Message correlation | Old assistant snapshot arrives during a new task | Rejected by task/conversation/turn/epoch identity |
| Duplicate send | Busy composer, partial paste, lost submit response | Reconcile before retry; no blind repaste or duplicate task |
| Guidance race | Late guidance for an older candidate or epoch | Revision conflict; current candidate unaffected |
| Queue cancellation | Reset queue while dispatch is pending, then send a new message | Cancelled completion cannot remove the new message; accepted remote actions are not falsely called recalled |
| Restart recovery | Crash after action begins but before result persistence | Unknown outcome retained; side effect reconciled before replay |
| Live status | Client reconnects with an event cursor | Ordered events resume without false completion or fabricated percentages |
| Self-update | Candidate starts but health/nonce/tool check fails | Old release restored; same task remains queryable; failed activation recorded |
| Migration | Crash during additive migration or incompatible schema candidate | Consistent recoverable state; incompatible candidate never accepts production writes |
| Windows processes | PID reused, child process hangs, DLL locked | Only owned process tree targeted; bounded failure and usable prior release |
| Sandbox | Test tries writing outside its directory/accessing secrets/network | Actual selected isolation boundary enforces the configured denial; weaker profile labeled accurately |
| UI/MCP parity | Change model/budget/feedback setting by chat, read UI, reverse change | Same persisted revision and effective value; restart requirement stated correctly |
| Fresh-chat continuation | New conversation requests continuation by project/task | Retrieves saved preferences, scope, source revision, candidate and next step; no need to reconstruct instructions from memory |

Performance targets for the first release, to be measured on this computer: warm bounded text search p95 under 500 ms on a representative 10,000-source-file corpus; overview/expand p95 under 1 second; no-op incremental refresh does not reread all file contents; control-plane status stays responsive during a build. These are proposed gates, not results from this audit. Record corpus size, excluded files, cold/warm state and background load. If a target fails, profile before adding models or services.

For coding, prioritize verified task completion and Hebrew constraint fidelity over throughput. Report per-task timings, timeout counts and memory peaks; a tiny successful sample cannot establish “Codex-level” quality. Keep costly/slow quality mode opt-in.

## 12. Operational recovery and user interaction

When a ChatGPT conversation stops working, the local task remains authoritative. `recovery_context(project_id, task_id?)` returns a small current summary, saved preferences/constraints, source/candidate identities, completed evidence, outstanding actions and exact next step. Provide handles for earlier relevant history instead of pasting an unlimited transcript. A new conversation gets a new consumer epoch and must rebind explicitly to the selected task; conflicting active directors cannot both mutate it.

Keep defaults at project scope, task overrides at task scope, and personal preferences at user scope. Mark provenance and update time. Future projects use the same schemas; do not hardcode TeleRus, Comics, Ember or one channel/voice into development/context code. In media projects, recovery can carry those user-selected values as data, but this plan does not change any media production workflow.

Status answers should report the actual phase, latest completed action, elapsed time, known wait reason and the next admissible step. Search/status requests do not wake a model. If the connection cannot receive proactive progress, explain that limit and expose the working durable-status route rather than pretending the client will automatically continue.

User-visible controls should cover: execution mode/director, selected coding model, optional CPU planner, measured memory profile, feedback connection, resource wait, cancellation, source-map search, saved annotations, candidate diff/tests, activation status and rollback availability. Technical diagnostics remain available without crowding the ordinary task flow. All labels, errors, tool instructions and model-contract messages use the project's localization system.

Log structured events with task/revision/source/worker/model IDs and durations. Redact secrets and omit full private source/transcripts by default. Diagnostic bundles contain only the relevant bounded artifacts and clearly identify anything not collected. Retain verified backups and source evidence until a deliberate retention policy removes redundant copies; never delete the only verified copy as cleanup.

## 13. Execution instructions for the implementing Codex

1. This document authorizes no runtime mutation by itself. Start implementation when the human requests it, using the current scope and existing authorization; do not repeatedly ask for routine reversible steps already covered.
2. Revalidate current source, versions, running tasks and hardware. This audit is a dated snapshot, not a guarantee that paths/settings are unchanged.
3. Read Phase 0 and finish it before introducing a second model or changing runtime startup.
4. Deliver Phase 1 early: real project mapping, keywords/tags/aliases and exact source access for ChatGPT, with no LLM needed for lookup.
5. Preserve useful APC logic and metadata, with source-hash attribution and tests. Use the newer pinned archive for code and preserve omitted older local evidence separately. Do not treat documentation `PENDING` as proof of missing implementation.
6. Complete online plan/patch execution before optional model-routing experiments. When ChatGPT directs, disable the redundant local planner for that task.
7. Benchmark one model for a whole phase. Install one challenger at a time only within the authorized implementation scope. Do not promise a particular model is best before evaluating it here.
8. Separate user-requested inference disable from internal resource release. At the end, unload only models owned by this work and verify it; leave other active user workloads alone.
9. Keep API, MCP, browser bridge and UI on shared contracts. Refresh tool discovery and exercise actual fresh-client paths; source code alone is not proof of connector availability.
10. Never overwrite the executing release as a self-update strategy. Use candidate -> evidence -> guardian activation -> observed health -> rollback when needed.
11. Test through the local agent's own runner for acceptance. Direct tool diagnostics and synthetic tests are useful evidence but must not be presented as autonomous success.
12. Report delivered behavior, test evidence and remaining gaps per phase. Update documentation/versioning when a real release is completed. Preserve all unrelated user changes and projects.

### Deliverables expected from implementation

- Reproducible source/release baseline and a verified restore path.
- APC reuse manifest and read-only metadata importer with conflict/freshness reporting.
- Working multilingual project intelligence in UI, local tools and MCP.
- Shared online/offline development workflow with durable guidance and evidence.
- Measured hardware/model profile and a reusable benchmark report.
- Searchable Ollama/Hugging Face model catalog, automatic compatible installation, durable download progress/recovery and role selection through both UI and natural-language chat.
- Guardian activation/rollback with failure-injection evidence.
- Fresh-chat recovery and tested UI/MCP configuration parity.
- Updated release documentation and exact known limits; no unsupported claim of perfect autonomous operation.

### Audit artifacts and sources

Local audit artifacts:

- This implementation specification: `C:/xampp/htdocs/dnd/output/docs/MellowCodex-Technical-Implementation-Plan-2026-11-07.md`.
- Newer APC source snapshot: `E:/AI/audits/apc-github-2026-11-07-da47822/apc-main`.
- Downloaded source archive: `C:/Users/MellowYak/Downloads/apc-main.zip`.
- Raw path/byte comparison: `E:/AI/audits/apc-github-2026-11-07-da47822/source-comparison.json`.
- Text-normalized comparison: `E:/AI/audits/apc-github-2026-11-07-da47822/normalized-comparison.json`.
- Selected reuse provenance: `E:/AI/audits/apc-github-2026-11-07-da47822/selected-reuse-manifest.json` (file hashes and intended destinations; no port is claimed complete).
- Older local APC source/evidence: `E:/APC_CORE` (preserved).
- Hub source inspected: `E:/AI/repos/local-agent-hub` (runtime unchanged by this planning task).

Primary external sources are linked beside the relevant decisions above. Their product capabilities and model listings can change; pin dependencies/artifacts and recheck official documentation during implementation. The APC reference is the user's private [repository](https://github.com/yodacoin/apc) at [the inspected commit](https://github.com/yodacoin/apc/commit/da4782284cff68e3310749583f6f0b26e0907d55). No credentials or private source archive have been published by this audit.


## 14. User additions and paused implementation handoff — 2026-11-07

The user authorized implementation, then explicitly paused it to continue in a separate MellowCodex chat. Do not continue implementation from the Ember Video chat. Resume only after the user instructs the new chat.

### Additional required product behavior

1. **Easy project onboarding and intelligent indexing.** Select a folder and click Index project, or ask in natural language to index that folder. Register the project, build a searchable map, show real progress and failures, then keep it current after edits, renames, deletions, terminal commands and Git changes. Support many projects without scanning entire drives or saturating CPU/RAM. Allow disabling background indexing per project. UI must show readable files, symbols, relations, counts and freshness; raw JSON belongs under optional technical details, not the main interface.
2. **Deterministic first, optional semantic enrichment.** AST/FTS/path relationships and aliases need no model. Local model or ChatGPT may add useful summaries/relationships when requested; record model/source hashes, provenance and confidence. Separate inferred annotations from observed facts and user-authored constraints. Never treat indexed text as permission. Avoid two resident models. All map/search/expand/annotation/status tools must be discoverable and usable through ChatGPT MCP, the browser director and the local agent.
3. **Git integration.** Check repository identity, branch, HEAD, staged/unstaged/untracked state and worktrees before edits. Preserve dirty work and unknown files. Support scoped diffs, branches/worktrees, selected staging, commits and user-authorized push/pull with conflict handling. Never force/reset/overwrite to hide conflicts. Handle unborn repositories and missing remotes explicitly. Test real temporary Git repositories, conflicts and dirty/untracked preservation through the agent. Do not claim perfect or error-free Git support from shell availability alone.
4. **Internal browser pointer.** Extend the existing Qt WebEngine/Playwright/CDP browser with visible virtual pointer motion, click/double-click, drag, scroll and keyboard actions tied to current screenshots/observations and viewport coordinates. It must not move the physical Windows mouse. Existing remote_input and browser_act are the foundation; avoid parallel browser engines. Add local-agent/MCP access, stale observation rejection and practical drag/click/scroll tests. A visual pointer overlay is presentation, not proof that input reached the page. The implementing Codex itself must still use only IAB for browser tasks.
5. **Coding model installation.** Qwen2.5-Coder 7B Q4_K_M was downloaded through the official local Ollama pull API and verified installed. It is a benchmark candidate, not an automatically selected superior model. Keep qwen3.5:4b as existing default until measured coding/Hebrew/resource results justify a change. The pull does not load GPU memory.

### Actual installed coding model

- Name: qwen2.5-coder:7b
- Parameters: 7.6B; GGUF Q4_K_M
- Size: 4,683,087,561 bytes
- Digest: dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364
- Evidence: E:/AI/audits/qwen-coder-download-20261107.json
- At pause: Ollama /api/ps returned no loaded models. Coding benchmark and selection remain pending.

### Current implementation state and known incomplete patch

See docs/DEVELOPMENT_IMPLEMENTATION_STATUS.md and docs/HANDOFF-2026-11-07.md. Context foundation has real local Engine and isolated IAB acceptance; the full plan is NOT complete and is NOT deployed to the production Hub. Last change added a draft durable indexing queue, project registration endpoints, background watcher and MCP registration functions. It has NOT been validated. In particular context.register_tool, context.index_status_tool and context.index_settings_tool locale keys are referenced but not yet authored: importing the new MCP registration can fail until completed. Do not restart the production gateway against this unfinished source. Finish and test the draft before activation.

## 15. Continuation audit against source and original chat — 2026-11-07

### Decision and evidence boundaries

Retain this plan and the existing implementation. A new research project or a wholesale rewrite is not justified by the chat transfer. The source architecture supports the proposed incremental approach; the gaps below require implementation and focused verification, not a second agent framework.

The actual source conversation is titled **בנה את מערכת Ember Table**, Codex thread `01a11fa8-42ea-71c1-9f92-7ade0ca7c9f9`. Its implementation turn, follow-up requirements and handoff were read using the thread API. The handoff's reference to an Ember Video chat is a naming discrepancy, not a change of project scope. Neither Ember product is the implementation target. The original and repository copies of this plan were byte-identical before this audit and are synchronized again afterward.

This audit inspected current Hub source, pinned APC contracts, recorded acceptance actions and fresh fixture results. No production service was restarted. No browser, new model inference, fresh ChatGPT conversation or real autonomous acceptance was run in this audit. Existing live evidence is explicitly historical. No external-source capability claim was refreshed; consult official documentation when implementing the dependent integration.

### Verified baseline and APC provenance

- All **24** selected APC file hashes match the pinned snapshot at commit `da4782284cff68e3310749583f6f0b26e0907d55`.
- The existing source backup contains **142** files whose archive contents match the source manifest. Persistent backup file hashes match; both backed-up SQLite databases pass read-only `integrity_check`.
- The backup manifest also lists `hub.sqlite3-wal` and `hub.sqlite3-shm`, which are absent now. Record this explicitly: persistent database hashes still match, but a literal all-entry verifier fails. Do not remove the original manifest or claim a completed application restore drill. The next baseline step must distinguish transient SQLite sidecars from portable backup artifacts and restore-test a disposable copy.
- Git still has untracked source and no remote. No commit, reset, branch replacement or publication was performed.
- Actual APC reuse remains **partial contract reimplementation** of `inc/project_map.php` and `api/project-map-search.php`, using Python AST/SQLite FTS5. The other 22 selected entries are design sources, not completed ports. PHP parity and the complete APC application were not executed.
- The previous real Engine acceptance artifact was reread: task `1ee1e46474b84c16b0a8e51df9b1cded`, Qwen3.5:4b, 31.64 seconds, context search/expand/related, source write, shell pytest exit 0, final `waiting_review`. Its action log also contains an invalid start=0 read and a rejected document_write before recovery. The summary tool list omits some failed calls; use full actions for audits, not only successful-tool summaries. This is a successful narrow repair, not broad coding equivalence or approval.

Reproducible fixture diagnostics and compact evidence: `E:/AI/audits/plan-reconciliation-20261107/probes.py` and `findings.json`. They operate on disposable fixture state, not user projects.

### Findings and required corrections

| Priority / component | Observed issue | Required behavior and acceptance |
|---|---|---|
| P0 MCP import — repaired in development source | Missing `context.register_tool` caused the existing integration test to fail before any MCP tool registration completed | Added all three missing descriptions in English, Hebrew and Russian. Fresh isolated gateway import succeeds; 36 focused tests pass. This does not activate production or make tools discoverable in an existing connector |
| P1 indexing lifecycle | `Indexing.request(..., enabled=False)` queues and executes another scan; a request arriving during a running scan is overwritten by `ready`, without a dirty generation for an immediate follow-up | Separate saved enable/disable from explicit refresh requests. Track request/completion generations, retries and ownership. Test requests during scans, disable, restart, shutdown and failure recovery through the shared service and all entry points |
| P1 mandatory context | A saved 6,000-character note with `must_not_break` can make `overview()` return no annotations because it breaks at the shared budget | Serialize required constraints separately from optional notes; include them or explicitly report a capacity limit. Never silently omit them. Test mixed projects and large annotations through the actual model packet |
| P1 freshness | Same-size content edited with preserved mtime is skipped and old content remains searchable; extractor version also does not invalidate the stat fast path | Add dirty-path/Git signals, extractor revision invalidation and bounded reconciliation. Expose index revision, coverage and freshness in search results; preserve exact hash checking for source expansion and before writes. A new coding task currently walks the whole tree via unconditional context_refresh |
| P1 scan bounds and exclusions | Scanner uses a fixed exclusion set and eligible-file limit, not Git inventory/ignore policy, total traversal bytes/time, resumable chunks or cancellation | Implement the section 6.2 policy. Test many excluded/non-source files, inaccessible/missing roots and large projects. Do not interpret an unreadable root as confirmed deletion of every indexed file |
| P1 onboarding/parity | Queue tools exist in MCP registration but not local tool definitions; the dialog renders primary results as JSON; settings/status UI and structured browser-director route are incomplete | Complete one shared service, readable map/progress UI and local/MCP/browser paths. Current discovered MellowCodex connector exposes only the seven older chat/task/file tools; new public context/index tools are not verified available here |
| P1 APC importer contract | Current synthetic import covers file-like documents. APC raw_terms are arrays; source_hash may be an entity hash, and path_or_route can be a route/selector. Current importer stringifies terms and compares supplied hashes to file bytes without typed provenance/conflict reporting | Add versioned, entity-aware fixtures based on the pinned producer. Distinguish file content hash from entity hash, normalize arrays, preserve origin and report incompatible/stale/conflicting entries. Do not call current synthetic coverage complete APC compatibility |
| P2 source map scope | Only Python has AST extraction; relationships are filename/module heuristics. No complete feature graph, rename identity, verified repair memory or obligation compiler | Preserve accurate labels, add adapters and tests incrementally; no claim that all APC subsystems were ported |
| P2 Git and pointer | Existing Git status/diff/worktree routes and internal remote_input are reusable, but worktrees assume HEAD and pointer supports click/text/key/scroll only | Extend these existing paths. Test unborn/dirty repositories and candidate snapshots; add virtual move/double-click/drag with fresh observation validation and verify no physical mouse movement |

### Revised execution order and completion gates

1. Preserve current source and finish the baseline restore drill, with a corrected portable-backup inventory recorded separately from the original manifest.
2. Keep the MCP locale repair; complete indexing lifecycle, mandatory-context and freshness fixes before activating the unfinished draft. Add meaningful regression cases for each reproduced failure.
3. Complete folder onboarding, readable map and background settings; expose identical saved state and execution through local tools, UI, MCP and browser envelopes. Measure multi-project responsiveness and cancellation, not only a two-file fixture.
4. Finish typed APC import and source/constraint coverage. Record each reused APC contract with source hash, destination, differences and evidence. Re-run real agent acceptance and inspect **all** actions, including retries/errors; independently verify IAB UI and fresh public ChatGPT discovery/use with models unloaded for deterministic operations.
5. Continue isolated candidates, scoped Git, director guidance and direct patches without a local model (Phase 2), extending current facilities. Preserve the standalone virtual-pointer workstream and its practical tests.
6. Continue Models catalog/install/select and resource leases, then measured single-model versus coder comparisons (Phase 3). The downloaded coder remains a candidate, not a new default.
7. Continue Guardian/rollback and release gates (Phases 4–5). Existing launch/admin-restart behavior is not transactional self-update. Publish only verified behavior and keep source/staged/active/client-verified states distinct.

All earlier requirements remain in force. Sections 2 and 14 are historical snapshots; this section and the implementation ledger govern the current continuation status. The full plan is not complete, and the successful locale repair is not a release or deployment.

### Implementation continuation after reconciliation

The first queue lifecycle fixes are now implemented in development source: separate background settings, durable request generations, and retention of requests arriving during scans. Eleven context/indexing fixture tests passed. This supersedes the disable/requeue findings for source behavior only; practical acceptance, shutdown tests, retry policy, UI/local-tool parity and remaining section 15 gates are still pending. No production activation.


### Additional requirement: optional conversation-memory verification (2026-11-07)

### Additional user requirement: PLAY connection and linked conversations

The ChatGPT connection control must offer MCP or browser PLAY side by side. PLAY uses the existing embedded-browser/controller/transcript path: connect the selected signed-in conversation, send versioned operating instructions and JSON request/result protocol, expose available tools/indexing/settings with actual capability limitations, and require no browser extension/plugin installation. The user may choose an existing conversation or ask the agent to open ChatGPT and create a new conversation automatically; authentication remains user-driven if required.

Persist a link between each local conversation and its chosen remote conversation/transport. Support named favorite remote conversations and reopening/resuming by selecting the local chat, without replaying old tasks or silently binding a different remote chat. Users can explicitly link/relink any local conversation; duplicate remote ownership and active-task transitions must be handled visibly. Hiding/closing the side PANE must not stop the background transport; distinguish this from closing the underlying browser tab/process, which requires restoration or an explicit disconnected state. Do not promise MCP fallback when no MCP client is connected. A future provider adapter can extend the same PLAY contract to Claude/DeepSeek; this is not presently verified support.

Acceptance: real existing/new-chat PLAY bootstrap, source-bound JSON round trip, indexing/settings request, progress/final reporting, deduplication after restart, favorite reopening, local-to-remote selection, pane hidden with transport still working, genuine tab-loss recovery, and MCP parity. All preference changes require shared persisted local/UI/MCP controls. Reuse current ChatGPTBridge/BridgeController/BridgeTranscript rather than adding a parallel dispatcher. This addition expands the active continuity goal; implementation and full browser acceptance remain pending.

Current evidence update: manual IAB ChatGPT review was accepted and later consumed by the local Engine (chatgpt-memory-feedback-live-20261107). This is not automatic local browser dispatch or deployed public MCP acceptance. Source-based decision retrieval now uses a native Hub FTS5 index plus linked correction expansion; the1,000-turn/26-anchor Engine case passed after two retained failures. Every request retains access to full chronological history; bounded model input and lexical matching limitations remain explicit. Future gates include paraphrases/unanchored decisions, complex conflicts, transport parity and public activation. No claim of unlimited model context.

The user requests an optional ChatGPT review of retrieved conversation memory, using the currently active browser-chat or MCP connection. Extend the existing director/bridge, not a parallel chat transport. Share only a bounded relevant excerpt, source conversation/task identifiers and exact source hash plus the claim/question. Preserve the original history; store reviews separately with provenance, timestamps and source revision. Outcomes must distinguish confirmed, contradicted and unavailable/insufficient context. ChatGPT must not claim it remembers an unavailable conversation, and its opinion alone must not overwrite local measured evidence. A stale source invalidates applicability of the review. Unavailable/disabled feedback falls back to local evidence without falsely reporting remote verification.

Expose enabled/disabled and transport preference through the same persisted service in UI, local tools and natural-language MCP. Browser transport may ask the connected chat; MCP is caller-driven request/response: expose pending review packets and accept correlated responses, with bounded waiting and no fictitious server-initiated ChatGPT calls. Do not resend on every read: cache by source hash + claim and invalidate after source changes. Never send unrelated history or credentials. Audit request, transport, waiting, response and fallback in the task timeline. Acceptance requires a real local-agent retrieval, browser/MCP parity, missing-context fallback, source-change/replay tests and an independently assessed memory answer. No percentage accuracy improvement is assumed without measurement. This requirement is planned, not yet implemented or deployed.

Implementation update: optional memory-review service, UI/local/MCP adapters, quote/source validation and local Engine request/fallback acceptance are implemented in development source. A real ChatGPT reply through the public connector/browser is NOT yet accepted. Browser extension enabling remains blocked after Qt lifecycle failure; shared management is a draft, not released support. None of this completes all plan stages.

Decision continuity implementation: exact user-request anchors retain source hashes and later supersession links; history is never replaced by inferred summaries. Latest eight anchors enter the bounded model packet; all others are paged. Local tool, HTTP/MCP source adapters and UI inspection exist. Real three-turn Engine acceptance with40 intervening turns passed (conversation-anchors-engine-20261107-b). Remaining gates include complex conflicting decisions, live remote feedback and public connector deployment.

### PLAY implementation checkpoint - 2026-11-07
Native Hub versioned PLAY protocol/tool catalog, per-chat transport/favorites/URL settings and new-conversation bootstrap are implemented. Shared HTTP/MCP controls and IAB settings persistence are checked;306 full fixtures and43 newest focused fixtures passed. No APC code copied for these features. Remaining acceptance: native signed-in browser bootstrap/response, hidden-pane continuation, restoring saved bindings after process restart, automatic source-bound memory feedback and public MCP. No production activation.


### Source-first comparison track — 2026-11-07
User requests two exclusive per-project modes for comparison, without damaging APC work. `fast` implements source-first exploration (inventory/instructions, search/read, dependencies/tests, bounded evidence, implement/verify); `apc_baseline` preserves the existing PARTIAL APC-derived index, not the complete upstream system. Separate source caches; one queue; shared explicit user constraints; no automatic dual scan. Native additions must not be reported as APC code reuse. Ember Video is a read-only acceptance project; compare source hashes/counts and evidence-backed feature planning, not exact wording. No Ember feature implementation or GPU generation is authorized by this comparison alone.

### Current user sequencing and general feedback requirement (2026-11-07)
Finish native local-only indexing/mapping acceptance first. External feedback is optional and general, not limited to indexing: either the local executor or the configured external director can initiate a task, send observations, request guidance/review and return corrections through MCP or PLAY Web. Reuse the existing director/feedback state rather than adding a competing workflow. Both modes use the same source map; initially exchange relevant path/signature/relationship capsules, then hash-bound line excerpts on demand. Headers alone are not semantic evidence. Delivery deduplication must be scoped to the external conversation/context and invalidated for changed content or unavailable prior context. This requirement is not yet a claim of end-to-end validation.

### Component and contract investigation — 2026-11-07
Implemented measured-map component selection, per-component relationship tracing, and static Python request-field/validator evidence. This is native fast-mode work, not additional APC reuse. Staged semantic contract composition is still not accepted: local model drafts and critics can both misinterpret dependencies. Keep local-only acceptance separate from optional GPT director integration; no production rollout or parity claim.

## 2026-11-07 — Local-model recovery audit checkpoint

Implementation was paused at the user's request for evidence-based diagnosis. The supplementary plan is E:/AI/repos/local-agent-hub/docs/LOCAL_MODEL_RECOVERY_PLAN-2026-11-07.md. It preserves the existing APC/index/runner/feedback work and prioritizes controlled source-packet and directed-step experiments before more implementation. The previous focused suite passed 94 checks; real semantic acceptance remains incomplete. This amendment does not mark the original phases complete or activate any change. This plan and its original copy have diverged; preserve both rather than overwriting either with the other.


## APC/SelfDevelop continuation audit — 2026-11-07

See APC_SELFDEVELOP_IMPLEMENTATION_PLAN-2026-11-07.md for a source-grounded update, actual reuse matrix and staged execution through an external MCP director. Preserve previous implementation and historical checkpoints; the new audit distinguishes current tested mapping from unported APC continuity contracts and incomplete control-plane self-update.
