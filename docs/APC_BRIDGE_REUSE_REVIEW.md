# APC bridge reuse review — 2026-11-07

The existing 24-item manifest records two partially reimplemented map/search contracts, two partial development-workspace contracts and twenty design candidates. These are selective reimplementations; no claim of copied bridge/runtime code or percentage of whole-project reuse is justified.

The new bridge candidate audit records exact source hashes. Useful gaps to investigate are console/page-error diagnostics, viewport overflow validation, learned application targets, managed process ownership and result-delivery outbox behavior. Standard browser navigation/input/capture already exists in hub/browser.py; replacing the Qt browser with APC's parallel runtime is not justified by source inspection alone. Hybrid snapshot capture explicitly calls itself fixture-only.

No APC bridge code was integrated during this review. Any extraction must keep source attribution, dependency notices, user-owned authorization and observed-target validation, and pass behavior plus actual agent acceptance tests. No unmeasured speed/reliability claim is made. PLAY, memory and AI connector cards remain native Hub implementations.
