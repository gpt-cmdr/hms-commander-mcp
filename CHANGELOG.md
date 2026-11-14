# Changelog

## [0.1.2] - 2026-11-14

### Changed

- Accept hms-commander 0.5 (`hms-commander>=0.4.0,<0.6`). hms-commander-mcp 0.1.1
  required `<0.5` and could not be installed alongside hms-commander 0.5.0. The
  server's text reads are unchanged; see COMPATIBILITY.md for the 0.5.0 evidence.
- The candidate content-API CI job qualifies the `v0.5.0` hms-commander release.
- Subagent-only routing guidance in the server instructions and tool descriptions (#6).

## [0.1.1] - 2026-10-07

- Include hms-commander-mcp in the opt-in `server_info(check_updates=true)` check (#4).

## [0.1.0] - 2026-10-07

- First release: bounded read-only HEC-HMS text information through MCP.
