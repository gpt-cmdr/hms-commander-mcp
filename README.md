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

This candidate is developed in public and has not been published to PyPI. From
its checkout:

```sh
python -m pip install .
hms-commander-mcp --root /absolute/path/to/project
```

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

The preferred adapter calls the new public `HmsText.parse_sections(content,
file_type)` API proposed in the companion HMS library change. It delegates
existing library parsing and performs no file I/O or project initialization.
Project/run reads require publication of that upstream API; the server does not
copy parsers or fall back to private methods.

On current PyPI **hms-commander 0.3.1**, Linux can read basin/met/control/gage
information through existing public standalone getters. A sealed in-memory file
snapshot supplies a stable path without writing any project or temporary file.
The transition contract is narrower: basin inventory contains primary scalar
fields, and met/control identities use filename stems rather than parsed section
names. Text `.hms` and `.run` reads fail clearly until HmsText is installed.
Windows has no transition adapter: it requires the upstream HmsText release.

POSIX input handling opens each path component with no-follow directory
handles. Windows input handling verifies the opened handle's final target lies
inside the configured root before reading and rejects leaf reparse points.
The native Windows file-policy subset passed 12 tests on Python 3.11.9. Full
Windows domain reads still need the upstream HmsText release and separate domain/
stdio qualification; do not infer those from file-policy results. Other platforms fail closed.
Each read runs in a separate killable process. No HmsPrj initialization, global
project selection, CRS detection, result loading, sidecar creation, or engine
lookup is invoked. The audited default logging setup uses stderr and no log file.

## Version and release policy

Dependency candidates: `mcp>=2.3.0,<3` (official SDK, no CLI extra) and
`hms-commander>=0.3.1,<0.4` (base only). Pydantic is explicitly declared
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
an update. The scheduled/manual dependency workflow compares stable PyPI metadata
and proposes a PR for compatible drift. Versions outside declared ranges are
reported as requiring maintainer review, never silently admitted. CI checks
minimum/current-stable installs and packaging; merge and publication remain human
steps. Publication of HmsText precedes claiming cross-platform project/run reads.

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

Published API baseline inspected: [hms-commander 0.3.1](https://pypi.org/project/hms-commander/0.3.1/).
HEC methods/terminology are primary HEC sources. This project's capabilities and
observations use its own package evidence. Repository writing instructions apply
to repository-maintained text, not users' external scripts/reports/deliverables.

## Qualification

On Linux CPython 3.11.2, 31 current-release/wheel contracts and 39 companion-source
contracts passed, including SDK stdio auto/legacy modes and bounded read-only
behavior. One explicitly enabled live PyPI metadata check passed. Linux minimum/latest CI passed on Python 3.10.21/3.11.16/3.12.14;
the native Windows Python 3.11.9 file-policy subset passed 12 tests without skips.
Full Windows domain/stdio qualification remains separate. [Validation details](VALIDATION.md) distinguish published
0.3.1 compatibility from unreleased HmsText source evidence.
