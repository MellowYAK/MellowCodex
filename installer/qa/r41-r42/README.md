# MellowCodex R41/R42 Windows VMware installation scripts

This directory preserves tested Windows guest installer scripts and QA launchers from 2026-11-24. The original R41 and R42 source archives, unsigned Broker package, user-specific QA logs, authorization keys, and service state are NOT included.

Guest INSTALL-1 PASS: Python 3.12.16, 127 pinned packages, Qt and Chromium.
Guest INSTALL-2 PASS: Native UAC-protected Guard and OwnerBroker.
Guest INSTALL-3 PASS: Guard localhost listener 8898, ordinary-user Hub and MCP gateway, OwnerBroker identity and runtime HTTP verification.
Still not separately proven: external ChatGPT MCP enrollment, Ollama availability, embedded browser content, VMware host-to-guest clipboard.

The QA scripts are not a complete standalone installer. Run using the separately supplied immutable full source ZIP and share folder layout. In the ordinary Windows guest user account run INSTALL-1.cmd, then INSTALL-2.cmd with approved native UAC, then INSTALL-3.cmd. The scoped GUARD-ACL-REPAIR.cmd adds read/execute only to immutable Guard release for original user and preserves SYSTEM/Administrators FullControl. FIX-GUARD-AND-FINISH.cmd invokes this repair before Stage3. Logs belong in shared QA-LOGS, never in Git.

R41 immutable archive SHA256:
580E647F4CA3E8C936FDF0170874CB8F0AA189B612936CF1F6851FC41AE7C53A
R42 immutable archive SHA256:
76AE0374957B06E95B1EC1DFA04763A97D343A34C3F6FAFF2D754A4C75DAF87A
R42 protected source SHA256:
7808B9EDC1CBE1674546F2F82917B8C77183E62BE7923ECE34E53ECFE1E890E8

Never commit auth.key, service account secrets, protected user state, ProgramData, private owner identifiers or user diagnostic logs.