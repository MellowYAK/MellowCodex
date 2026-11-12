# Release notes: Guard, Hub, Gateway and connector health

Date: 2026-11-12
Repository: MellowYAK/MellowCodex
Branch: main
Implementation commits:
- 02f8e156f0e29c79afdb12c197d7b9dcfdcc9935
- 86942a0d9a4de2ab3d122b9c93e49a4385dfb41f

## 1. Guard, Hub, Gateway and Relay health

- Hub update supervisor now starts BOTH Hub and local MCP Gateway after its owned-service stop, even when a relay is enabled. Previously the gateway could be skipped while health verification still required it.
- Hub HTTP health uses a bounded, more tolerant client instead of the original 2-second urllib probe that produced intermittent false negatives. Actual HTTP failures still fail the health check.
- Gateway /health retries transient Hub readiness errors, disables proxy inheritance for loopback access, and keeps returning HTTP 503 if Hub cannot be verified.
- Relay PowerShell status now imports Microsoft.PowerShell.Utility before Get-FileHash to avoid false JSON decode errors.
- New recovery, ownership, Gateway and HTTP health regression tests.

### Mellow Guard service health

The separately installed immutable Mellow Guard release is 0.1.1-ef91a6a0d0706d91.

- Guard status(service_id=hub) may return healthy=true based on independent verification of the existing Hub and Gateway, even if another authorized manager started them.
- observed_healthy verifies exact executable, parent process, startup argv, working directory, birth time, socket ownership and repeated live HTTP responses.
- supervisor_healthy remains separate and means Guard itself started/tracked the processes.
- started_pids remains empty when Guard did not start them. Healthy service observation does not mean Guard adopted processes or gained permission to terminate them.
- docs/validation/guard-observed-health-release-20261112.patch contains the exact source delta. This is a reviewable patch, NOT the installed Guard release binary or a production config export.

## 2. Deterministic file handoff between tools

- Added hub/file_handoff.py with opaque, source-bound observed file references.
- list_files now returns exact references; read_file accepts either a ref or the existing explicit path parameter.
- References are checked for task match, current observation, file identity, stale content and directory misuse before ordinary workspace/owner policy checks.
- Explicit-path operations remain supported. Correct source identity does not by itself guarantee the model picked the intended reference initially.

## 3. Evidence freshness for external MCP connectors

- The health report now distinguishes local_overall_status, external_connectors_status and full overall_status.
- On cached snapshots, the connector proof, Gateway/Guard Gateway dimensions, Relay tunnel evidence and all summary statuses are recomputed together.
- Protected Guard HTTP 401 can be counted as locally operational only when exact owned process+port evidence is paired with a fresh, REAL authenticated Guard MCP call.
- External connector proof remains append-only with the existing 120-second TTL. Local HTTP, TCP and SSH process checks cannot create an external ChatGPT MCP proof.
- If no fresh external MCP request succeeds for 120 seconds, connector evidence correctly changes to stale. The code does NOT automatically call out to ChatGPT or mark stale evidence green.

## 4. Verification and release safety

- Baseline source suite before first Git commit: 41/41 tests passed.
- Isolated Guard observed-process adversarial tests: 8/8 passed, with an additional actual read-only service probe reporting observed_healthy=true.
- Connector freshness/proof tests passed 22/22 then 25/25; final installed regression suite 29/29.
- Local deployment updates reached ACTIVE_VERIFIED through the control-plane supervisor, with old revisions retained.
- Live ChatGPT MCP responses from both MellowCodex and Mellow Guard were observed and their actual timestamps recorded. A fresh health snapshot then reported overall=operational, local=operational, external=operational.
- Guard separately returned healthy=true, observed_healthy=true and supervisor_healthy=false with basis verified_existing_services.
- Authentication/permissions, process receipts, old release and user data were preserved by owner-authorized release switching.

## 5. Limitations and exclusions

- The external evidence expiry after 120 seconds is intentional and still applies. Persistent green without a fresh authenticated external event would be misleading.
- Health verification and process ownership remain separate from supervisor startup provenance.
- This change does not replay uncertain actions or grant itself new privileges.
- Unrelated pre-existing browser, desktop, UI and work-in-progress files were not staged or committed.
- No auth tokens, private keys, runtime receipts, current.json, user conversations or health evidence JSON were committed.

## Related source and verification files

hub/guardian/control_plane.py
hub/mcp_gateway.py
hub/service_health.py
hub/health_diagnostics.py
hub/service_health_ui.py
hub/file_handoff.py
hub/tools.py
docs/validation/file-handoff-2026-11-12.md
docs/validation/connector-evidence-refresh-20261112.md
docs/validation/guard-observed-health-release-20261112.patch
tests/test_connector_evidence_reconciliation.py
tests/test_guard_external_proof_correlation.py