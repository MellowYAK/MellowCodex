# Live runner acceptance: final failed-step closure (2026-11-08)

## Scope
Real MCP SelfDevelop runner acceptance in a separate synthetic chat. This is not a fixture or a manual database transition.

- Synthetic conversation key: `test:failed-closure-live-20261108`
- Synthetic chat ID: `4b492d1950704aa3aaa612f9fd2165c0`
- Failed command task ID: `7d5e8b3e86e04a7baf3bb2c90e954988`
- Exact command: `Write-Output 'EXPECTED_FAILURE'; exit 7`
- Observed tool: one `run_shell` with `shell=powershell`, `exit_code=7`, `output=EXPECTED_FAILURE\r\n`, `failure_kind=shell_execution`.
- Action ID: `26af3b84ebfe4f16910808695f732cff`, complete; no pending action reported.
- Actual task state after failure: `waiting_user`, revision 5.

## Real state-machine blocker
The running Hub's `/api/tasks/{task_id}/review` implementation permits `reject` only for `waiting_review`. For a `waiting_user` task the supported review action is `request_changes`, which requeues the same task. It therefore cannot explicitly review a failed shell execution into terminal `failed` without adding a supported transition. Do not edit the database or force a state.

The new `selfdevelop_close_failed` endpoint was installed in the previous Mellow Guard update, but the ChatGPT MCP catalog did not expose the tool in this session after the reported refresh. No closure was executed. Because the preceding task remained `waiting_user`, no subsequent success command was submitted, to preserve the SelfDevelop review gate.

## Prior deployment evidence and limitations
- Candidate: `0878dd3533db4547a22cacd2eea9910b`, revision 10.
- Mellow Guard update: `9b08a3d8209e45f09767ea1c1e60fa2d`, reported `ACTIVE_VERIFIED`.
- Focused isolated candidate tests: 32 passed in 10.75 seconds, `verified=true`.
- This live acceptance **did not pass**; isolated tests used synthetic `store.update` to construct final failed and done states. That was insufficient evidence of real runner transitions.
- Corrective work needed: implement explicit, audited transition from `waiting_user` after director-reviewed final failure into `failed` (without replay, pending-effect bypass or auto-skipping), then expose and verify `selfdevelop_close_failed` through a refreshed MCP catalog, and rerun the actual two-command sequence.
- The earlier refresh of MCP tools successfully exposed `selfdevelop_prepare_update`, `selfdevelop_activate_update`, `selfdevelop_update_status` and `selfdevelop_command`. It did not expose the newly installed `selfdevelop_close_failed` in this ChatGPT runtime.

No change to unrelated chats, models, deployment state or task database was made by this documentation step.

## Follow-up: real runner acceptance of both supported recovery paths (2026-11-08)



The initial blocked finding above is historical. Two distinct recovery paths were subsequently verified with actual MCP runner actions, not synthetic store.update fixtures. No DB edits, model loading or state-machine changes occurred.



### Path A: correct the SAME waiting_user task

- Synthetic chat ID: 4b492d1950704aa3aaa612f9fd2165c0

- Task: 7d5e8b3e86e04a7baf3bb2c90e954988

- Original run_shell action 26af3b84ebfe4f16910808695f732cff executed Write-Output 'EXPECTED_FAILURE'; exit 7 once. Observed EXPECTED_FAILURE, exit 7, waiting_user revision 5.

- Director selfdevelop_command_correct with request live-command-correction-20261108-001, reviewed reason, current revision 5, exact command Write-Output 'RECOVERY_NEXT_STEP_OK'.

- New run_shell action d821784f6c8147f3bc1d9316d5aa0ba1 returned RECOVERY_NEXT_STEP_OK and exit 0.

- Action log showed exactly two commands, once each; original exit-7 command was NOT replayed. Director selfdevelop_review approved at revision 9; task DONE revision 10.



### Path B: reject reviewed result, close failed, run a NEW task in SAME chat

- Wrong task: 7eecb1d176a64053ab1691ba707d6c4f

- Real run_shell action 6e1693e90e7f4c6f8253c24c309b55ea executed Write-Output 'WRONG_RESULT', returned WRONG_RESULT, exit 0, entered waiting_review revision 5.

- Director selfdevelop_review rejected it for semantic mismatch (required RIGHT_RESULT), producing FAILED revision 6 through the existing supported review transition.

- Refreshed MCP catalog exposed selfdevelop_close_failed; called with matching chat/task, expected_revision 6, request live-close-reviewed-failed-20261108-001 and concrete reason. Returned CANCELLED revision 7. No pending actions observed.

- Next task: d76e154f4a71499db890f413f63856cf. run_shell action 232de5e7f3634c7f84da2942235a786c executed Write-Output 'RIGHT_RESULT', produced RIGHT_RESULT, exit 0. Director approved at revision 5; DONE revision 6.

- The rejected task was not replayed; all earlier task goals, review and action records remain retained.



### Outcome

Path A proves reviewed command correction in the original stopped task. Path B proves explicitly reviewed semantic failure, audited terminal closure and successful NEXT task in the same chat. Both are actual runner receipts. This is supervised recovery acceptance, not autonomous development acceptance.
