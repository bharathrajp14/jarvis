# Changelog

All notable BR-JARVIS changes are documented here.

## [41.0.0-production-hardening] - 2026-08-19

### Security

- Made REST and WebSocket authentication fail closed with one canonical, strong `JARVIS_SERVER_API_KEY`.
- Removed loopback authentication bypasses and long-lived WebSocket query keys.
- Replaced browser API-key persistence with HttpOnly sessions and one-time WebSocket tickets.
- Added WebSocket origin validation and strict session-cookie defaults.
- Fixed Career and static-file path traversal and arbitrary existing-file disclosure.
- Changed permission defaults from unrestricted execution to destructive-action confirmation.
- Made incomplete mutating-tool metadata derive high risk, local-system permission, and approval requirements.
- Disabled unisolated host code execution and in-process community plugins by default.
- Replaced plaintext credential values with OS-keyring-backed opaque references and atomic metadata writes.
- Removed a tracked nested API-key file, expanded secret ignore rules, and added a secret baseline gate.
- Removed vulnerable ChromaDB from default dependencies, upgraded `cryptography`, and moved AGPL-risk PyMuPDF behind an explicit extra.

### Runtime

- Added typed agent outcomes for verified success, partial execution, failure, cancellation, and timeout.
- Added task deadlines, cooperative cancellation acknowledgement, and bounded graceful queue shutdown.
- Added bounded in-memory event retention, asynchronous JSONL persistence, file rotation, and shutdown flushing.
- Ensured synchronous event publication delivers asynchronous subscribers when no event loop is active.
- Added deterministic web-lifespan cleanup for task queue, event store, logging, and orchestrator.

### Packaging and delivery

- Moved FastAPI to `brjarvis.web.api` and PWA resources to `brjarvis.web.static`.
- Added packaged PWA and skill resources; retained a deprecated `apps.web.api` compatibility adapter.
- Consolidated metadata in `pyproject.toml`; reduced `setup.py` to a legacy shim.
- Added platform markers, missing `python-multipart`, OS keyring, and patched cryptography dependencies.
- Replaced unsafe setup fallbacks with project-local virtual-environment installers.
- Quarantined the root `brjarvis.py` launcher to prevent package shadowing.
- Replaced the unreachable CI chain with independent quality, test, package, architecture, security, secret, dependency, and license gates.

### Product contracts

- Aligned Career dashboard job search, resume generation, ATS scoring, and spreadsheet synchronization with canonical OpenAPI routes and payloads.
- Added an executable dashboard/OpenAPI contract test.

### Verification

- Final regression result: **295 passed, 1 skipped, 2 benchmark tests deselected**.
- Incremental Ruff gate passes.
- Hardened Pyright scope reports zero errors.
- Import Linter keeps the security/presentation boundary.
- Bandit hardened-surface scan passes.
- `pip-audit` reports no known vulnerabilities.
- License policy passes for the installed environment.
- Final wheel installs outside the checkout, builds 51 routes, finds packaged PWA assets, and passes dependency integrity.

### Breaking and operational changes

- A unique `JARVIS_SERVER_API_KEY` of at least 24 characters is mandatory for the web control plane.
- Code execution requires explicit `JARVIS_ENABLE_UNSAFE_HOST_EXECUTION=true`; this is not recommended for production.
- Community plugins require explicit `JARVIS_ENABLE_UNTRUSTED_PLUGINS=true`; only trusted code should be enabled.
- `apps.web.api` is deprecated; import `brjarvis.web.api`.
- ChromaDB is not installed by the default memory extra pending an upstream security fix.
- PyMuPDF requires the explicit `pdf-rendering` extra and a separate license review.
- Any real credential previously committed must be rotated outside the repository before production release.
