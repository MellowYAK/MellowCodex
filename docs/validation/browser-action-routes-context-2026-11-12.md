# Browser Action Routes context and visual editor (2026-11-12)

## Implemented
- Sanitized HTTP(S) route start URL and before/after page URLs for each step; password, query and fragment are not retained.
- Reused existing route editor, editable step notes and instructions, uploaded reference screenshots, and source-bound historical evidence.
- Display historical source-page links using noopener noreferrer.
- Journal route runs by chat, task and revision; add runs/resume to the visual editor and natural-language MellowCodex MCP tool.
- Read-only resume exposes browser action IDs, last observed URL, uncertain effects and instructions for fresh inspection. It NEVER automatically replays an uncertain click or submission.
- Existing owner permissions, project sharing, evidence hashes and revision checks are preserved.
- Only exact app.py router/asset allowlist and index.html CSS/JS integration is added to the Git baseline; unrelated work stays uncommitted.

## Acceptance
21/21 focused installed browser/action tests passed, and 14/14 MCP regression tests passed after the additional tool change. Hub and Gateway HTTP 200, headless installed Microsoft Edge UI smoke passed (script, buttons, dialog, zero JavaScript page errors), both deployment updates ACTIVE_VERIFIED.

## Limits and recovery
Historical URLs are redacted to origin/host/path; token-bearing query strings are intentionally discarded. This is verified persistence and safe guidance, not a guarantee an arbitrary external web workflow will automatically recover. The previous health-green-2026-11-12 Git tag remains immutable for recovery. Never use git reset --hard on an active dirty workspace.
