# Compatibility evidence and release prerequisites

Qualification date: October 4, 2026. Package identities and MCP protocol revision
are separate. Minimum and latest-compatible stable releases were identical on
this date: official MCP SDK **2.3.0**, HMS Commander **0.3.1**.

| Dependency/environment | Evidence |
|---|---|
| Official MCP SDK 2.3.0 | Typed schemas, actionable errors and stdio auto/legacy modes passed locally |
| Published HMS Commander 0.3.1 | Linux public standalone getter contracts passed on real repository text fixtures |
| Companion HmsText source, unreleased | Content API and upstream fixture contracts passed locally; not published evidence |
| Linux CPython 3.11.2 | Read-only/path/encoding/bounds/timeout/concurrency/status and package checks passed |
| Linux Python 3.10.21/3.11.16/3.12.14 | Six minimum/latest-compatible jobs passed: 31 tests and1 optional-network skip each; pipcheck and builds passed |
| Windows CPython 3.11.9 | Native file-policy subset passed 12 tests with no skips; full domain adapter not qualified |

See [VALIDATION.md](VALIDATION.md) for exact checks, source provenance and limits.
A resolver range is not proof that every version has passed qualification.

Current-release transition permits approved basin/met/control/gage reads on
Linux using existing public getters and sealed memfd snapshots. This is a
compatibility bridge, not a second domain parser. HmsText replaces it through
capability detection. The transition omits gage type because the current public
getter can default a missing source `Type` to `Precipitation`; MCP does not present
that default as an observation. Empty met/control getter records are also omitted; this does not establish
that the source lacks a named section header. HmsPrj.initialize is excluded because even with DSS loading
disabled it invokes SQLite/CRS discovery. No heavy extras are requested, but base
HMS dependencies remain installed.

Project/run reads and all Windows domain reads require the upstream HmsText
release. Publish it before claiming those capabilities against PyPI or raising
the wrapper minimum. Windows CI currently qualifies secure text I/O and path
policy separately, not the unreleased full domain adapter. Native link denial
can be skipped if the host lacks link privileges; inspect CI skips before release.
No binary, GIS, Java or engine case is included in MCP qualification.

CI exercises declared minimum and latest-compatible public dependencies,
functional contracts and wheel/sdist builds. Latest/minimum behavior and updated
metadata must be reviewed before changing ranges or publishing. Preserve user
pins; no runtime auto-upgrade, unattended merge or publication.

Remote evidence: [run 37165170753](https://github.com/gpt-cmdr/hms-commander-mcp/actions/runs/37165170753),
source head 8e04b3c, all 7 jobs successful. Windows policy coverage includes traversal,
extensions/streams, unconfigured roots, NUL/oversize inputs, real text reads and
leaf link denial. It does not establish Windows HmsText domain/stdio behavior.
The earlier cancelled Windows run had no retrievable diagnostic log; its stall
cause remains unconfirmed.
