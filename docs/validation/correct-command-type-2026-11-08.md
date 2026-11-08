# Validation: `correct()` command type guard (2026-11-08)

## Defect
In `hub/development/commands.py`, `correct()` called `command.strip()` before validating the type. Non-string commands such as `None`, `123`, and `True` could raise `AttributeError` instead of the expected `ValueError`. This validation error must occur before any task mutation.

## Minimal correction
The isolated candidate inserts `not isinstance(command,str)` before `not command.strip()` in the existing `if` condition. It retains the previously existing PowerShell/cmd shell whitelist, blank-command rejection, 20,000-character limit, timeout integer/bool/range checks, function docstring, and unrelated logic.

The new file `tests/test_correct_command_type.py` parametrizes `None`, `123`, and `True`, checking `ValueError` and unchanged task revision, state, and result. Existing test modules were preserved.

## Observed candidate validation
- Candidate ID: `7f0b6152f99e4af6993df817bc062edf`.
- At candidate revision 1, `pytest tests/test_selfdevelop_commands.py tests/test_correction_timeout_contract.py tests/test_correct_command_type.py` returned **21 passed in 8.20s**, exit code 0, no source changes.
- After README and CHANGELOG documentation updates, the same three-module command at candidate revision 4 returned **21 passed in 18.98s**, exit code 0, `verified: true`, `source_changed: []`.
- The director inspected `candidate_diff` and confirmed the original command guard branches and module docstring remain. A line-ending-only README regression was corrected before documentation approval.
- The first SelfDevelop task failed because the local model was unloaded and attempted an out-of-scope tool, then was cancelled at revision 5. Subsequent documentation edits used director-authored `exact_patch`, not autonomous model reasoning.

## Deployment and limitations
This is isolated candidate verification, **not production installation**. At the time of writing, Mellow Guard control-plane prepare/activate/status tools were absent from the current external MCP catalog. No Hub/MCP restart, production health check, reconnect proof, Git publication, or autonomous self-development acceptance is established by the above tests. The user plans to perform activation through the existing product API. The full product scope remains open.

This file records observed evidence available before the final documentation-only candidate revision test; that subsequent test receipt must be inspected separately and must not be assumed to have passed merely from this document.
