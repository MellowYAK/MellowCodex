# Architecture

The Qt desktop client and optional HTTP UI submit tasks to one FastAPI service on loopback. A single asyncio scheduler owns model and desktop execution. Ollama serves one Qwen3.5 4B model; the tool loop sends native tool schemas and attaches only the newest screenshot to model input.

SQLite stores task revisions, messages, immutable events, and action intent/results. Before a side effect starts, a pending action is committed. A cancelled or uncertain side effect cannot be automatically resumed: a user must reconcile what actually happened. Microsoft Agent Framework FileCheckpointStorage saves a projection of each committed task revision, and SQLite records its checkpoint reference. SQLite remains authoritative if a crash occurs between the database commit and file save.

File tools resolve paths within the selected workspace and back up overwritten files. PowerShell is explicitly unrestricted at the current user's privilege level and is not a sandbox. The desktop driver requires a recent screenshot and unchanged foreground HWND before sending input, then captures a new observation. Windows-MCP is used only for optional accessibility reading; it does not independently own mouse/keyboard execution. One Windows process lock prevents two Hub runners from recovering or mutating the same queue.

Task completion requires declared file criteria; tasks without such checks, and all desktop tasks, await human review. Review rechecks hashes of evidence and rejects outdated revisions or externally changed evidence. These checks are a workflow gate for trusted local use, not isolation from processes that have the user's filesystem privileges.

OpenCode runs on an optional authenticated local server and has a separate adapter. It is not yet the Hub's executor. The local MCP supervision process exposes task submission/status/control; human review is intentionally omitted from its tool list.

The application owns Qt WebEngine with a persistent profile and loopback CDP, driven by Playwright. A single-instance tray runtime survives closing the window. Browser DOM observation remains available without screenshot rendering. Optional site-scoped Chrome session transfer uses a user-installed extension and an expiring one-use pairing code.

Further work: integrate a single OpenCode owner into Hub scheduling; implement bounded Workflow graph orchestration; test real desktop workflows and game input; implement and prove reboot reconciliation; then run the source plan's acceptance matrix before labeling production readiness.

Windows WTS session state gates physical input. Known no-input deferrals enter waiting_desktop, release the engine lock, and resume when the session becomes active. UI Automation patterns use a dedicated COM thread and require post-action verification.
