# Computer shutdown / כיבוי מחשב

Use when the user requests computer shutdown or asks to inspect shutdown readiness. This package never invokes Windows shutdown directly. It is an action-routing skill for the existing privileged, owner-gated MellowCodex computer power tools.

For preview: call extension_run(name="computer_shutdown", arguments={"action":"preview"}), then call the native computer_power_preview(action="shutdown") and show impact. To power down, require an explicit current user request and confirmation of the task impact. Then call the native computer_power(action="shutdown",request_id=<fresh stable id>,confirm_tasks=true). This native operation preserves owner authorization, drain/rollback checks, journal and non-forced shutdown. Do not interpret installing this skill or previous unrelated approval as authorization to turn off the computer.

For durable status: run the skill with {"action":"status","operation_id":"..."} then invoke computer_power_status. Never replay a request with uncertain outcome. If the native computer_power tools aren't available, report the missing tool, don't call shutdown.exe, subprocess, PowerShell Stop-Computer, or hub.power.submit directly.

Installation / tests do not shut down or restart the machine.
