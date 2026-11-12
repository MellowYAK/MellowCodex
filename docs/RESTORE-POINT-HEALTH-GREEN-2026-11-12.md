# Verified local-health restore point — 2026-11-12

Tag to create: health-green-2026-11-12
Project: MellowYAK/MellowCodex
Baseline verified main commit (before this document): eb4dc2ecec428ec436ba1b272200c29982ae9eec
Implementation commits: 02f8e156f0e29c79afdb12c197d7b9dcfdcc9935, 86942a0d9a4de2ab3d122b9c93e49a4385dfb41f
Detailed change notes: docs/RELEASE-NOTES-HEALTH-2026-11-12.md

## What is known to work

Read-only live service-health test on 2026-11-12 observed Hub, local MCP Gateway, Mellow Guard, Guard Gateway, Ollama, model service, owner broker, recovery, desktop and SSH relay reporting operational. The authenticated Mellow Guard MCP status query returned healthy=true, observed_healthy=true and supervisor_healthy=false because Guard did not itself start those Hub processes.

After genuine completed ChatGPT MellowCodex and Guard MCP calls were recorded as externally verified observations, the installed health dashboard returned:
- overall_status=operational
- local_overall_status=operational
- external_connectors_status=operational

This is a timestamped acceptance result, not a perpetual guarantee. External connector proof expires after 120 seconds without another verified remote MCP call; a correct system may then display stale or unverified. Ollama model qwen2.5-coder:7b was configured and inferencing enabled but the model was not loaded in GPU memory at rest.

Previously measured regression tests: 41/41 baseline tests, 29/29 connector proof tests; Guard-specific ownership negative cases passed 8/8. The tested code changes and limitations are in the release notes.

## Local Guard version and limits of the Git checkpoint

Installed immutable Mellow Guard release: 0.1.1-ef91a6a0d0706d91
Its prior immutable release was retained locally.
Guard supervisor source delta in this Git tree:
docs/validation/guard-observed-health-release-20261112.patch

Git saves tracked code and this documentation. It DOES NOT back up Windows services, the installed immutable Guard release, private configuration, OAuth consent, private keys, user projects, conversations, local databases, active task states or other runtime evidence. Do not copy secrets into the repository. For actual disaster recovery the operator must also retain the independently managed authorized local backups.

## Safe Git recovery workflow

1. First preserve any unfinished working-tree changes and user data separately; DO NOT reset --hard in an active working tree.
2. In a **new empty checkout**, fetch tags and inspect this checkpoint:

       git fetch origin --tags
       git show --no-patch --decorate health-green-2026-11-12
       git switch --detach health-green-2026-11-12

3. Read docs/RELEASE-NOTES-HEALTH-2026-11-12.md and the tests before deploying.
4. Validate pinned dependencies, local ownership/permissions, Guard release identity and authorization. Use the supported owner-controlled Guard deployment and rollback workflow. Do not copy the Guard source diff directly over an installed release.
5. Verify independently: Hub 8876 HTTP 200; MCP Gateway 8897 health HTTP 200; Guard Gateway 8896 HTTP 200; authenticated Guard MCP reports healthy=true; Guard protected HTTP endpoint 8898 may return HTTP 401 to unauthenticated probes; complete actual ChatGPT MCP requests and review the resulting local/external health snapshot.
6. Keep the previous installed Guard release and service backups until the new deployment is verified.

## Exclusions and integrity

This restore tag and document deliberately exclude the pre-existing approximately 98 unrelated modified/untracked working-tree entries. They are not part of this tested baseline. Secrets, access tokens, local process receipts, evidence JSON and personal content are not stored here.