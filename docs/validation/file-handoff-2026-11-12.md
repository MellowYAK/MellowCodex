# File handoff: deterministic file references (2026-11-12)

Candidate: `4564529de0ac4097b4c2e8d626a62526`.
Runtime status: staged in isolated candidate; NOT installed in live Hub/MCP.

## Evidence

- `tests/test_file_handoff.py` and `tests/test_file_handoff_integration.py`: **7 passed in 2.01s**, candidate revision 6.
- Verifies 32-character update ID `961841f95a974b459b05396bd6bfe2f7`, unrelated sibling reference, stale metadata, foreign-task reference, directory rejection, path+ref exclusivity, ToolRunner list_files→read_file and visibility of the resolved full path to the normal owner-policy gate.
- One earlier combined run of unrelated existing tests reported 3 failures: pre-existing fixture tasks omitted the `revision` field expected by owner-policy code. These failures have not been corrected or claimed as passing.
- No test in this report proves operation after restarting live Hub/MCP. This awaits deployment and a live read-only end-to-end check.

## Security/compatibility

Directory entries can be handed to the next `list_files(ref=...)`, then file entries to `read_file(ref=...)`, without copying an update ID manually. Verified by the ToolRunner integration test using the full 32-character directory ID. References are selected from the most recent per-task listing and checked against the task ID and unchanged file metadata. They are not permissions. Paths are resolved before the ordinary owner-policy and workspace checks. Legacy `read_file(path=...)` remains supported. File identifiers are not interchangeable across tasks; missing/stale references fail closed.

## Current limitations

A model can still choose the wrong reference, just as it can choose the wrong entry in a visible list; the mechanism guarantees exact resolution of the *chosen* reference and avoids string reconstruction, but does not infer the user's intended selection. Because the mechanism is not deployed yet, live behavior is unchanged.
