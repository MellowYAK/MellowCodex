# System resource snapshot (global MellowCodex skill)
When: read-only local CPU usage, RAM capacity, disk usage and process count. Not for termination, surveillance, cloud access or configuration changes.

Discovery: in ANY future authorized MellowCodex code/desktop task use built-in extensions_list; find name system_resource_snapshot; then extension_run. Reuse tested existing version, do not redownload or rewrite.

Run input JSON: required sections is a nonempty unique array of cpu, memory, disk, process_count, max four. Optional disk_path is an existing absolute local path and requires disk. Unknown fields rejected.
Example 1: {"sections":["cpu","memory"]}
Example 2: {"sections":["disk","process_count"],"disk_path":"C:\\"}
Invoke extension_run with name system_resource_snapshot and arguments equal to the chosen JSON.

Verify extension_run exit_code=0, stdout JSON verified=true, backend psutil, expected section keys, and registered version; otherwise report failure. CPU is a brief live sample.

Provenance: original adapter using official https://github.com/giampaolo/psutil API; installed psutil version 7.2.2; upstream BSD-3-Clause license. No upstream code copied or dependency downloaded. Canonical source scripts/skills/system_resource_snapshot.py and independent test scripts/skills/test_system_resource_snapshot.py. Installed globally in E:\AI\extensions\system_resource_snapshot with hash-pinned version manifest, not a chat-scoped artifact.

Learn capability X: GPT directs executor to call extensions_list first. If missing verify authoritative source, license and available dependencies, create a parameterized original adapter plus separate test and English instructions in stable workspace, register with existing extension_register, verify receipt, add provenance/license/tags/input schema to SAME manifest, then extension_run. Later chats list and reuse version with different arguments. Instruction-only notes are not executable tested skills. No model-weight training or unrestricted autonomous downloads.
