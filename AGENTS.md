# Project maintenance instructions

The user requires every fix, update and upgrade to be documented.

- Update CHANGELOG.md for every user-visible change and every material internal fix. Record the version/date, concrete changed behavior, validation actually performed, and known limitations. Do not invent historical releases or test results.
- Keep README.md current when capabilities, operation, configuration, persistence, networking or limitations change. Describe the final behavior, not merely the implementation plan.
- During development, record changes under Unreleased. Before delivering a completed update, move them into a dated version entry. Use patch increments for fixes/documentation-only releases and minor increments for added capabilities; group changes delivered together in one release and list each separately.
- Keep pyproject.toml, hub.__version__, README's version and the changelog release synchronized. The FastAPI app imports hub.__version__; do not hardcode a different API version.
- Record actual test results in VALIDATION.md when behavior is tested. Distinguish mock/fixture tests from real desktop, browser, phone, locked-session and reboot tests.
- Never include credentials, cookies, hub.key contents or temporary login links in documentation or version history.

## Agent-owned execution

- When the user reports that the local agent failed, repair the shared planning, tools, dispatch, verification or feedback mechanisms. Do not complete the business task manually and present that as the local agent's success.
- Regression fixtures and direct adapter diagnostics are development evidence only. End-to-end acceptance must use the local agent's own task runner and its recorded actions and outputs.
- Keep fixes independent of a particular model, website, task ID or conversation. Describe any actual limitation instead of promising perfect future execution.
- A documentation/version update alone does not require restarting the user's running agent or browser. Report if a running process still needs its next normal restart to load changed metadata.

## Natural-language MCP configuration

- Every new or changed user-configurable setting must also be readable and changeable through MCP tools, so the user can request it in ordinary language in ChatGPT without JSON, shell commands or manual file edits.
- Keep UI and MCP on the same persisted settings and validation. Give tools clear descriptions of the setting, accepted values, effects and prerequisites so the calling model can map natural-language requests correctly.
- Confirm the saved values after changes and report whether they are active, require restart or are blocked. Never imply a setting is deployed from code inspection alone.
- Document MCP availability alongside UI settings; validate both paths for setting changes.

## Git publication workflow

The user authorizes publishing this project to https://github.com/MellowYAK/MellowCodex. After each coherent completed and validated code change, create a descriptive commit and push through the local agent, verifying the remote commit. Never publish credentials, runtime state, private conversations, browser profiles or audit artifacts. Inspect staged content and preserve existing remote history; never force-push or reset to hide divergence. Record failures precisely and continue the authorized development after resolving them. Publication is not a production deployment.
