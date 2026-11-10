# Skill Shops live acceptance — 2026-11-10

Installed update: addf954ac1174906b1371a0fed4b090e, ACTIVE_VERIFIED.
Candidate: 771c93417ec6428e8ee41f3a7aa9af9d revision 3.
Sixteen focused candidate tests passed; four catalog tests passed before the final busy-gate refinement. JavaScript syntax passed with the installed Playwright Node runtime.

Live acceptance used isolated Chrome and actual Settings > Skill Shops buttons with the existing selected conversation and protected OwnerBroker Full policy. No owner permissions were changed.
- Installed shop-demo: HTTP 200, functional test passed.
- Ran the installed tool: returned skill=shop-demo, version=1.
- Updated through UI: HTTP 200, immutable version changed.
- Removed through UI: HTTP 200, package moved to quarantine.
- Original installed count remained 23; original 100 mapped capabilities remained intact.
- Screenshots and detailed receipt: E:/AI/artifacts/skill-shops-live-20261110/.

Initial navigation/encoding attempts failed before mutation; corrected acceptance completed. Unit checks cover rejected owner bindings, stale source, failed-update preservation, protected coverage, and active-task gating.

Scope: local packaged Python skills only. Remote ZIP marketplace downloads, malware sandboxing, fresh Ask-mode owner approval and real failed-update rollback were not exercised in the live UI run. Existing Full policy authorization was verified; failed-update preservation was tested in isolated fixtures.
Runtime/package version remains 0.15.3; updater refuses any pyproject change without a separately prepared environment. Dependencies were preserved byte-for-byte.
