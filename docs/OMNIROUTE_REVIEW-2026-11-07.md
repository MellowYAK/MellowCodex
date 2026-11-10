# OmniRoute selective reuse review

Source: https://github.com/ChrisCompton/omniroute
Pinned commit: `515674b6cf7cc29b3db027c9119e9b2ef12e0ba7`.
Downloaded to `E:\AI\audits\omniroute-review-20261107`; not installed or started.

## Findings and decisions

| Source | Useful behavior | MellowCodex decision |
| --- | --- | --- |
| `src/shared/constants/providers.ts` | Provider identity and authentication categories | Extracted 72 unique provider entries as a research seed. OAuth/API Key are authentication methods, not providers. Catalog presence does not establish compatibility, credentials, availability or connection. Audio, image and search providers must not automatically become text directors. |
| `open-sse/config/providerRegistry.ts` | Separate provider protocol configuration | Adapt into native provider profiles with explicit capabilities and transport. Do not install a second gateway. |
| `open-sse/services/combo.ts` | Model selection and fallback strategies | Reimplement only needed health/availability routing. Fallback must not silently replace the selected director or replay an uncertain write. Routing is not work delegation. |
| `src/shared/utils/circuitBreaker.ts` | Persisted failure state and bounded recovery probes | Useful design for unavailable external providers; integrate with existing error/event reporting rather than introduce a second task system. |
| `open-sse/services/comboAgentMiddleware.ts` | Model affinity and scoped tools | Persist affinity in our database, not tags inside assistant text. Keep explicit validated tool allowlists; invalid restrictions must not expand access. Do not replace all existing system instructions. |
| `src/lib/a2a/taskManager.ts`, `taskExecution.ts` | Task IDs, state transitions, terminal-state protection | Keep existing MellowCodex durable task runner, review gates and conversations. Add parent/child relationships there. Do not copy its separate task manager or default five-minute lifetime. |
| `src/lib/skills/a2a.ts` | Memory-aware routing interface | Inspected handler returns an automatic provider recommendation and a message that memory must be loaded. This is not implemented project understanding. Keep APC and native source indexing. |

## Transport boundary

OmniRoute's reviewed routing is primarily provider API/protocol routing. Its MCP/A2A interfaces expose gateway operations; they do not establish a working browser-chat adapter for every listed provider. Our MCP server lets a connected external director call local tools. Calling an external model requires a configured outbound API adapter or a functioning Web PLAY session. An inbound MCP connection alone is not an outbound model client.

Keep the existing ChatGPT PLAY adapter. Other providers need separate tested adapters, login state and conversation ownership. Serialize operations on each browser conversation, even when independent API workers run concurrently. Never label a provider connected solely because it exists in the catalog.

## Native Work Delegation implementation sequence

1. Shared persistent provider profiles and capability discovery for UI and MCP. Distinguish catalog, configured, connected and execution-tested states.
2. One selected director per parent task; explicitly assign bounded subtasks and permitted context. Workers return proposals and evidence, not changes to the live project.
3. Director reviews each proposal. Approved exact changes enter existing candidate/Guidance execution with file hashes and revisions. Local execution returns results to the same director for review.
4. Persist dependencies, ownership, request IDs, failures and review decisions in the existing chat/task history. Resume after restart without replaying uncertain actions. Avoid concurrent writes to the same files.
5. Validate one actual director-worker-executor-review cycle before broader provider support. Check API and PLAY separately; no claim of support from fixtures alone.

## Reuse status

Only provider metadata has been extracted, under `docs/third-party/omniroute-provider-catalog.json`; it is deliberately not an unused runtime module or a claim of implemented connections. MIT attribution is preserved in `docs/third-party/omniroute-LICENSE.txt`. Source hashes and exact provenance are recorded in `docs/third-party/omniroute-reuse-manifest.json`.

No executable OmniRoute code was integrated in this review. No models were loaded, services restarted, dependencies installed or production routes changed. Work Delegation and additional provider adapters remain implementation work, not completed features.
