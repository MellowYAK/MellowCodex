# Release 0.17.1: GPT-directed exact MCP executor correction (2026-11-08)

This patch is confined to hub/development/selfdevelop.py and tests/test_objective_authorization_idempotency.py. Byte-identical replay of an existing authorized objective request after the mapping task reaches done is idempotent and read-only. A changed request, cross-chat replay or fresh authorization without the review gate remains blocked.

Candidate 4c9e771fa50c4320b46160fcb02dc821 revision 1, task ffb03fbbf0ea4e9a837ff86ae539ea2e done rev6; test-019636fd46fe4805ab0a2e9207165119.json: 19 passed in 30.58 seconds, verified=true, source_changed=[]. Reviewer B approved only the two exact source/test paths. Guard update af565cd45e71443e999b04fd2565aac4 reached ACTIVE_VERIFIED; both live installed hashes match the candidate and Guard journal.

The acceptance scope is GPT director through MCP and the local exact executor. Local-model planning/autonomy is deferred. Optional selfdevelop_run_objective chat 0f8ac1936e52470ea41ab86a8d60f689 failed before write at context budget and remains reconcile_required. This is a failed/incomplete experiment. The actual guided completion belongs in original chat 8cae5657612a4fbeb390c51a8201fb64. Local installation and reconnect evidence are NOT an automatic ChatGPT callback, and full completion requires verifying the actual report in that source chat.

Source publication to PR #1 does not merge, restart or deploy additional live code.
