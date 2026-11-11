# Internal browser operation and recovery (0.24.0)

Use ordinary browser chat for a goal and the **Task guidance** control on a browser/desktop task card for a correction. MCP uses the existing task_guidance_status/task_guide revision protocol; stored conversation mirroring is not a substitute. The local model makes choices from current Playwright/CDP DOM evidence, exact labels/states and coherent images. OCR is fallback. Discovery remains available through tools_enable/extensions; no new permission is granted by tool visibility.

The workflow is observe, choose an authorized action, inspect its measured effect, continue, then assess fresh evidence for the requested entity. Submitted actions are never inferred complete from prose alone. Resume reuses durable actions and corrections; uncertain effects must be reconciled. Passwords the agent does not know, required owner consent and unsupported site challenges can require the user.

This release was tested on a disposable multi-step setup with and without director feedback and on individual Hebrew, English and Russian public pages. It is not a universal human replacement. Multi-site tasks may still stall. A heavy page caused a native Qt GUI hang; automatic recovery of that failure is not certified.

## Recovery and rollback

Inspect task state and pending effects first. Do not replay a completed submission to obtain a fresh-looking receipt. Use the existing service health panel to distinguish Hub/MCP failure from a hung desktop. A CDP listener alone is not healthy browser evidence. Native IPC also timing out and Windows reporting a hung window require bounded owner-supervised desktop recovery; preserve the profile, tab inventory and any active work. Do not terminate unrelated processes or automatically reopen the offending page.

The independent SelfDevelop/Guard update journals contain changed-file backups and hashes. Latest update e80ff041a85246eba94738e37458860d is ACTIVE_VERIFIED. The existing recover option is for interrupted updates; it is not a rollback button for an already verified update.

For a deliberate rollback, prepare a new isolated candidate restoring the browser release's reviewed runtime files from published release/task-lifecycle-0.23.0 (commit 4bc9446d81606af763a7a79f40249c380e98fa33), preserve later unrelated edits, run the focused compatibility checks, then use candidate_test, selfdevelop_prepare_update and selfdevelop_activate_update while tasks are idle. Synchronize version-only metadata separately; no dependency install or database downgrade is required. Keep durable tasks, actions, chats, projects, skills and browser profile. A full rollback activation drill has not been performed.

## Safe computer power

Settings > General and the independent Health & Services window expose safe Shutdown/Restart. MCP uses the same persisted operation backend. Inspect the impact preview, then use the existing owned-service drain. Busy work or unverifiable service/desktop stops must block Windows power. A disconnected MCP connection is not proof of physical power-off. This release does not bypass those checks.
