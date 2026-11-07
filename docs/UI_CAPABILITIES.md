# UI and capability comparison — 2026-11-05

Official sources consulted directly:
- https://learn.chatgpt.com/docs/windows/windows-app
- https://learn.chatgpt.com/docs/features
- https://learn.chatgpt.com/docs/projects
- https://learn.chatgpt.com/docs/browser
- https://learn.chatgpt.com/docs/reference/settings

The user supplied the visual reference. This is an independently implemented interface with Local Agent branding, not an OpenAI client or a claim to reproduce proprietary services.

| Capability | Local implementation |
|---|---|
| Left project/chat sidebar, light/dark themes, mobile drawer | Implemented |
| Persistent chats, rename, pin, archive, search | SQLite; shared between desktop and mobile |
| Conversation context | Last 12 turn prompts/results, current attachments, saved project instructions; full transcript retained in SQLite |
| Add computer folders | Authenticated remote folder chooser; existing local directories |
| New independent Git worktree | Creates a new branch and registers the worktree as a project; isolated fixture tested |
| File explorer/previews | Project-confined text previews, up to 500 KB |
| Git review | Status, diff statistics and unstaged patch; no fake merge/publish controls |
| Terminal | Explicit bounded PowerShell commands; not a full interactive PTY |
| Attachments | Up to 5 local images/text files, 2 MB each; vision images passed to local model |
| Computer actions | Existing screenshot, native input, accessibility and locked-session handling |
| Built-in browser | Native Qt WebEngine beside the chat; mobile DOM/screenshot/control pane |
| Chrome sessions | Existing site-scoped optional user-installed bridge |
| Stop/pause/resume and result review | Existing engine controls exposed on turns |
| Read-only planning | Read-only mode; no dedicated plan approval state machine |
| Durable recovery | SQLite + checkpoint files; uncertain side effects require reconciliation |
| Scheduled tasks | Local recurring chat tasks with interval, capability mode, pause/resume; emergency stop disables schedules |
| Plugin/skill store and third-party account connectors | Not replicated; existing MCP supervisor and Windows adapter only |
| Voice/dictation, image generation, cloud agents | Not implemented; no controls pretending otherwise |
| OpenAI model/account features and production parity | Not supplied by the local Ollama model |

Validation: 44 Python tests, extension mock test, HTTP UUID fallback test. Actual two-turn local-model UI test confirmed memory and history after reload, with zero page errors and no horizontal overflow at 390px. Native Qt offscreen renders inspected at 1440x900 and 390x844. Rendering/testing used our application, not an external personal browser.

## Universal application targeting and ChatGPT handoff — 2026-11-06

Application tools discover executable identity and HWND independently of browser DOM. `app_open` restores/opens the specific installed application and reports verified foreground/non-minimized state. `window_inspect` prioritizes all tab labels and their selected states before document controls. Embedded browser outputs identify their source explicitly. A live local-model regression used app_find + window_inspect and correctly reported Walla plus a selected Chrome New Tab; it did not inspect the unrelated embedded Google page.

The direct ChatGPT connector uses the user-visible chatgpt.com tab in Qt WebEngine; no MCP server or private ChatGPT API. The user connects a tab and signs in there. Questions can be sent from the interface or via chatgpt_ask. An explicit objective can enable bounded automatic handoff: assistant action envelopes become local tasks, then actual results/tool evidence return for review. Screenshot attachment is attempted only when an unambiguous image input is exposed. Duplicate IDs are rejected; uncertain sends stop; process restart requires reconnection; emergency stop disables the handoff. Cloud login and page structure are dependencies; tests using fake messages do not prove the logged-in site works.
