# Focused edits for the isolated coding worker

The worker supports both legacy full-content proposals and focused proposals containing `path`, `base_hash`, `find`, and `replace`. Its trusted normalization layer must validate the supplied read-only packet source, allowed paths, writable flag, exact SHA-256, unique match and non-no-op. The replacement is assembled in memory, preserving bytes and CRLF outside the selected span; the model has no I/O or shell tools.

Existing Development.repair retains ownership, candidate hash/revision preconditions, syntax checks, bounded retry/test feedback and director verification. New tests: tests/test_worker_focused_edits.py; compatibility tests: tests/test_coding_worker.py. Model-proposed fixes remain separate from proof of test success; staging and Mellow Guard deployment require explicit director review.

Prior observed local Qwen attempts returned unchanged_source or invalid/untrusted proposals, not successful autonomous repairs. Refresh tools earlier resolved exposure of the Mellow Guard MCP operations.

## Candidate runner bytecode-cache regression

A separate preexisting flaw was reproduced with original `hub/development/runner.py`: source `value=1` generates a timestamp-based `.pyc`; changing the source to `value=2` with identical size and modification second caused the second test invocation to continue reporting `assert 1 == 2`, exit 1. Clearing only the temporary cache restored exit 0. `run_pytest` now assigns a fresh temporary `PYTHONPYCACHEPREFIX` for each subprocess, automatically cleaned up when that run finishes. It does not delete project or user caches. The acceptance test `tests/test_runner_pycache_isolation.py` failed before and passed after this focused fix. On candidate revision 12, the 15 selected tests including the previously failing order passed (15 passed in 11.40s); standalone focused/new tests also passed (15 passed in 13.38s). The model worker remains a bounded patch-only component, and deploy/semantic acceptance still require director review.
