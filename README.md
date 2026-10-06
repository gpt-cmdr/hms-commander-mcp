# HMS Commander MCP

HMS Commander MCP supplies bounded information from HEC-HMS text files. It is
an independent CLB Engineering project that complements HEC's work; it is not
associated with or endorsed by HEC. Technical terminology follows HEC's
[HEC-HMS documentation](https://www.hec.usace.army.mil/confluence/hmsdocs).
Those links are passive references; the server does not retrieve HEC pages.

## Purpose and boundary

Use this server through a **bounded informational subagent**. The parent supplies
one question, a configured project root, named file/entities, selected fields,
and row/character/time budgets. The child returns a compact answer with source
identity, versions, units/time basis, counts, truncation, and blockers. The host
must expose project MCP tools only to that child. A server cannot attest whether
a caller is a subagent. A host without isolation should use a scoped Python read
instead of exposing these tools to its main coordinator.

The server reads approved project/component text, scalar parameters, gage
configuration, and control/run relationships. It does not modify projects,
compute models, download data, export files, or read DSS/HDF/SQLite, coordinates,
geometry, rasters, grids, or spatial results. Filenames and DSS pathnames are
references only and are never followed. Text-series/report extraction is deferred
until a dedicated upstream public reader can provide a qualified contract;
there is no generic file reader. Larger investigations use public
[hms-commander Python APIs](https://rascommander.info/hms/) and their required
extras outside MCP.

## Install and configure

Use Python 3.10+ and an authorized managed environment. Version 0.1.0 is on PyPI:

```sh
python -m pip install --upgrade hms-commander-mcp
hms-commander-mcp --root /absolute/path/to/project
```

A client that launches servers through uv can run
`uvx hms-commander-mcp --root /absolute/path/to/project` instead of a separate
install; uv builds and caches the environment on first launch. Content reads use
`HmsText` from hms-commander 0.4.0, which a new install resolves. Preserve an
existing pin or lock when required.

Repeat `--root` for additional allowed roots. Requests name the exact normalized
configured root; client protocol roots never expand the allowlist. Use stdio;
logging goes to stderr. Keep the server in a managed environment with read-only
project access where practical. No Java, HEC executable, GIS, DSS, or CNG extras
are needed. The base HMS library still brings pandas/numpy/requests/tqdm; this
wrapper does not claim to eliminate mandatory upstream dependencies.

For a host that supports subagent-only tool routing, configure this command:

```json
{
  "mcpServers": {
    "hms-commander": {
      "command": "hms-commander-mcp",
      "args": ["--root", "/absolute/path/to/project"]
    }
  }
}
```

This command configuration alone does not establish subagent isolation. Configure
that separately in the host/plugin before using project reads.

Claude Code users should install the `ras-commander@ras-commander-plugin` plugin
from the [gpt-cmdr/ras-commander-plugin](https://github.com/gpt-cmdr/ras-commander-plugin)
marketplace (forthcoming; the repository is not yet published). The plugin covers
the HMS and RAS text servers. It declares the server at plugin level, supplies a
plugin subagent for bounded reads, and adds a `PreToolUse` guard that denies
project tools to the main session. A subagent-only isolation check passed in
Claude Code 2.1.287 on October 5, 2026. The plugin does not copy agent files into
the user's `~/.claude/agents` directory. Other hosts require their own isolation
configuration.

## Update an installation

Close the MCP client before updating so that no running server holds the
environment. `server_info(check_updates=true)` reports the latest stable PyPI
versions of hms-commander-mcp (from 0.1.1), hms-commander and the MCP SDK beside
the installed versions without changing the environment. On 0.1.0, compare
`package_version` with the [PyPI project page](https://pypi.org/project/hms-commander-mcp/).

**Managed pip environment.** Name both packages:

```sh
python -m pip install --upgrade hms-commander-mcp hms-commander
```

pip's default upgrade strategy keeps an installed dependency that still satisfies
the requirement, so upgrading only `hms-commander-mcp` can leave hms-commander
0.3.1 in place.

**Cached `uvx hms-commander-mcp`.** Keep the client configured with the plain
command. Each launch resolves current compatible releases, but uv reuses its
cached PyPI index data while that data is fresh (PyPI currently allows
10 minutes). To use a new release immediately, run once:

```sh
uvx --refresh --from hms-commander-mcp python -c "from importlib.metadata import version as v; print(v('hms-commander-mcp'), v('hms-commander'))"
```

The command refreshes the index data, builds the current environment and prints
both versions. The next plain `uvx hms-commander-mcp` launch reuses that
environment. `uv cache clean hms-commander-mcp hms-commander` has the same effect
on the next launch; name both packages so the domain library is also resolved again.

**`uv tool install hms-commander-mcp`.** `uvx` prefers an installed tool to its
cache, and `--refresh` does not change that tool. Run
`uv tool upgrade hms-commander-mcp`.

These uv results were observed on October 5, 2026, with uv 0.12.23 on Linux,
using a local index that served older and newer RAS Commander MCP wheels with
PyPI's cache header; the HMS refresh command was run against PyPI and reported
hms-commander-mcp 0.1.0 with hms-commander 0.4.0. Preserve deliberate pins and
locks; no tool call installs or upgrades packages.

## Windows long paths

Version 0.1.0 opens validated project files through Windows extended-length paths
(`\\?\` and `\\?\UNC\`), so files beyond the 260-character `MAX_PATH` limit
are readable. Root, traversal, opened-handle and reparse-point checks are
unchanged. Other tools in a workflow, including Python scripts, may still fail on
long paths. An administrator can enable Windows long-path support from an
elevated prompt:

```bat
reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f
```

Or in an elevated PowerShell session:

```powershell
New-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force
```

No reboot is needed; processes started after the change use the setting, and
running processes, including an open MCP client, must be restarted. Each
application must also declare long-path awareness.

## Tools and budgets

| Tool | Contract |
|---|---|
| `server_info` | Installed package/library/SDK versions, capabilities, approved fields, limits; optional `check_updates: true` fetches bounded stable PyPI metadata |
| `read_hms_sections` | Typed `request` object with root, relative file, matching kind, optional exact name/type, fields, offset, limit, character budget, and deadline |

Approved extensions: `.hms`, `.basin`, `.met`, `.control`, `.run`, `.gage`.
Files must be regular text, at most 2 MiB. Read requests have at most 100 rows,
16,000 serialized result characters (including the SDK text fallback indentation), 30 seconds, and two concurrent workers.
Default query: 20 rows, 8,000 characters, 15 seconds. Unknown fields are rejected.
The return envelope includes source-relative file, SHA-256, byte count, encoding,
installed library version, selected adapter, units/time caveats, total and returned
counts, next offset, truncation, and rows. Source text is data, never instructions.

Example arguments:

```json
{
  "request": {
    "root": "/absolute/path/to/project",
    "file": "event.control",
    "kind": "control",
    "fields": ["start_date", "start_time", "end_date", "end_time", "time_interval"],
    "limit": 5
  }
}
```

Intervals retain source spelling; missing timezone or interval units are not
inferred. No precision rounding, unit conversion, computation, or hydraulic/
hydrologic suitability determination is performed. Pagination offsets apply to
the same file/name/type/field selection; verify the returned hash before combining
pages if the project may change. Oversized rows fail with a request to narrow
fields or use Python. No raw attributes, coordinates, free-form descriptions,
unknown parameters, or repeated storm-depth records are emitted.

## Public API and platform compatibility

The preferred adapter calls the public `HmsText.parse_sections(content,
file_type)` API published in **hms-commander 0.4.0**. It delegates existing
library parsing and performs no file I/O or project initialization. All six file
kinds, including project and run relationships, are read through HmsText on
Linux and Windows. The server does not copy parsers or fall back to private methods.

**hms-commander 0.3.1** remains supported only as a Linux transition. There, the
server reads basin/met/control/gage information through existing public
standalone getters. A sealed in-memory file snapshot supplies a stable path
without writing any project or temporary file.
The transition contract is narrower: basin inventory contains primary scalar
fields, and met/control identities use filename stems rather than parsed section
names. Text `.hms` and `.run` reads fail clearly until HmsText is installed.
Gage type is omitted in the transition adapter because the public getter supplies
`Precipitation` when the source omits `Type`; that default is not reported as an
observed source value. HmsText reports `Type` only when present. Empty met/control getter records are also omitted; this does not establish
that the source lacks a named section header.
Windows has no transition adapter: it requires hms-commander 0.4.0.

POSIX input handling opens each path component with no-follow directory
handles. Windows input handling verifies the opened handle's final target lies
inside the configured root before reading and rejects leaf reparse points.
Native Windows reads with hms-commander 0.4.0 are covered by the corpus results
under [Qualification](#qualification). Other platforms fail closed.
Each read runs in a separate killable process. No HmsPrj initialization, global
project selection, CRS detection, result loading, sidecar creation, or engine
lookup is invoked. The audited default logging setup uses stderr and no log file.

## Version and release policy

Declared dependencies: `mcp>=2.3.0,<3` (official SDK, no CLI extra) and
`hms-commander>=0.3.1,<0.5` (base only). Pydantic is explicitly declared
for the typed contracts (already required by the SDK); packaging supplies standard
version comparison. This range is an implementation target,
not a claim that every version has passed qualification. See
[COMPATIBILITY.md](COMPATIBILITY.md) for exact evidence and release prerequisites.

Runtime reports installed versions without installing or upgrading packages.
`server_info(check_updates=true)` explicitly opts into fixed official PyPI metadata
endpoints, capped at 512 KiB per package and a five-second worker deadline. Offline
or unavailable metadata is reported; the default makes no network request.
Users retain their pins/locks. New managed installs should resolve current
compatible releases; refresh a managed environment explicitly after inspecting
an update (see [Update an installation](#update-an-installation)). The
scheduled/manual dependency workflow compares stable PyPI metadata and proposes a PR for compatible drift. Versions outside declared ranges are
reported as requiring maintainer review, never silently admitted. CI checks
minimum/current-stable installs and packaging; merge and publication remain human
steps.

## Specification and sources

Implemented against the official [Python SDK v2](https://py.sdk.modelcontextprotocol.io/),
its [tool contracts](https://py.sdk.modelcontextprotocol.io/servers/tools/),
[structured output](https://py.sdk.modelcontextprotocol.io/servers/structured-output/),
and [stdio specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio).
The SDK owns negotiation and wire serialization; this package does not recreate
initialization/discovery. Official SDK auto and legacy client modes passed local
stdio contracts; this does not establish compatibility with every host.
Annotations describe behavior; roots, field selection, file validation, isolation,
and result bounds enforce it. No sampling, elicitation, remote transport, task,
resource, audio, image, or UI feature is enabled merely because MCP supports it.

Published API baselines inspected: [hms-commander 0.4.0](https://pypi.org/project/hms-commander/0.4.0/)
(HmsText) and [hms-commander 0.3.1](https://pypi.org/project/hms-commander/0.3.1/)
(Linux transition).
HEC methods/terminology are primary HEC sources. This project's capabilities and
observations use its own package evidence. Repository writing instructions apply
to repository-maintained text, not users' external scripts/reports/deliverables.

## Qualification

Version 0.1.0 with hms-commander 0.4.0 read a corpus of 586 HEC-HMS text files
with 0 errors on Linux and on Windows from a UNC project root. The 44 corpus files
whose Windows path reached 260 characters passed after the extended-length change
(PR #2). The PyPI
packages reproduced the results obtained from source. These are read-contract
results, not engine, hydrologic or all-client acceptance.

Before hms-commander 0.4.0 was published, 31 current-release/wheel contracts
and 39 companion-source contracts passed on Linux CPython 3.11.2, including SDK
stdio auto/legacy modes and bounded read-only behavior. Linux minimum/latest CI
passed on Python 3.10.21/3.11.16/3.12.14, and the native Windows Python 3.11.9
file-policy subset passed 12 tests without skips. [Validation details](VALIDATION.md) and [COMPATIBILITY.md](COMPATIBILITY.md)
record both stages.
