# Direct MCP recovery checkpoint — 2026-11-18

## Verified working runtime
The source baseline is bb7ccfe0d9bf61d97e325ef583ff9cb8568ccbe1. Exact SelfDevelop PowerShell execution does not invoke a local model. The original protected owner broker remains mandatory. A healthy service alone does not prove the executor has the correct token.

## Incident and root cause
The broker was running; installed client SHA-256 matched the reviewed source pin. Elevated local client returned `Pipe is broken` / identity verification false. An ordinary non-elevated interactive PowerShell returned verified identity. Task Manager showed elevated Codex Hub and Gateway. After stopping only the owned Codex Hub/Gateway and starting the pair from ordinary PowerShell through the existing service reconciler, actual MCP PowerShell returned exit 0. The protected owner service was not altered. The startup script previously called an admin alignment module capable of elevating the executor, contrary to the broker's ordinary-token requirement.

## Real acceptance
- Direct read-only PowerShell output: DIRECT_MCP_POWERSHELL_OK; exit 0.
- A new directory outside the source repository was created; text file written and read back exactly; a PowerShell script created and executed with expected output; both file hashes recorded in the local task log.
- ELEVATED=False; ACCEPTANCE_OK=TRUE; model_inference_complete=false. Model was not loaded and inference was disabled.
- No Yak source, policy, protected broker binaries or Guard source changed.

## Restore procedure and limits
Use the supported service controller, stopping only owned Hub and Gateway with preflight/task checks, and start the pair from an ordinary interactive PowerShell. Do not use an elevated executor, weaken verification, or bypass owner approval. The original protected broker must verify the connection and authorize the action. Both existing logon tasks were Limited/Interactive. This checkpoint documents a live verified recovery; permanent startup/shortcut correction and actual reboot verification are separate milestones. Apply the same reviewed ordinary-user execution contract to Yak later, with its own broker and product-specific paths.
