# Authenticated connector evidence refresh (2026-11-12)

The installed health diagnostic separates local service health (local_overall_status) from the freshness of authenticated external MCP evidence (external_connectors_status). overall_status reflects both dimensions.

- External evidence expires after the existing 120-second TTL. Expired evidence is never presented as a current ChatGPT round trip.
- On snapshot cache reuse, connector status, Guard/Gateway connector dimensions, relay tunnel evidence and overall statuses are recomputed together.
- A protected Guard API returning HTTP 401 can be marked locally operational only when its exact owned process and port are verified and a recent actual authenticated Guard MCP call has been observed.
- Neither local HTTP 200 nor the presence of an SSH relay is sufficient proof of ChatGPT connectivity.
- A real acceptance check recorded MellowCodex and Guard MCP responses and returned overall/local/external = operational; separate regression tests cover expiry and failed authentication.

Limitation: this does not initiate remote ChatGPT requests autonomously. If no external MCP call occurs within 120 seconds, the connector evidence correctly becomes stale; local services can stay operational.
