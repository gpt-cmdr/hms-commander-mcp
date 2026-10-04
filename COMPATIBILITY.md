# Compatibility evidence and release prerequisites

Research baseline: October 3, 2026. Package identities and MCP protocol revision
are separate. Values below are candidates, not proof of runtime compatibility.

| Dependency/environment | Target | Evidence at implementation handoff |
|---|---|---|
| Official MCP SDK minimum | 2.3.0 | Official v2 documentation inspected; runtime checks pending authorization |
| Official MCP SDK latest compatible stable | Resolve within >=2.3.0,<3 | Scheduled/manual metadata PR proposes drift; no automatic publishing |
| HMS minimum/current PyPI | 0.3.1 | Standalone getter source inspected; Linux transition adapter, runtime checks pending |
| HMS latest compatible stable | Resolve within >=0.3.1,<0.4 | Contract/packaging CI candidate; range widening requires review |
| HMS companion HmsText source | Unreleased | Pure content API implemented upstream; project/run and Windows reads require its release |
| Linux CPython 3.10–3.12 | Initial matrix | Functional/platform checks pending authorization |
| Windows CPython 3.10–3.12 | Pure HmsText path | Handle containment implemented; native Windows qualification required |

Current-release transition permits approved basin/met/control/gage reads on
Linux using existing public getters and sealed memfd snapshots. This is a
compatibility bridge, not a second domain parser. HmsText then replaces it
through capability detection. HmsPrj.initialize is excluded because even with
DSS loading disabled it invokes SQLite/CRS discovery. No heavy extras are
requested, but base HMS dependencies remain installed.

Before release: qualify read-only file evidence, symlink/traversal denial,
Unicode/encoding handling, omitted coordinate fields, unknown fields, row/
character bounds, timeout/concurrency/cancellation, structured result schemas,
stdio roundtrips, baseline/latest installed APIs and wheel/sdist metadata. Include
real repository fixture provenance and exact successful versions in this file.
Publish upstream HmsText first, then revise the server's minimum version only
when that release is qualified. No runtime auto-upgrade or unqualified support
claim is appropriate.
