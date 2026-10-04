# HMS MCP validation

Date: October 4, 2026. User authorized planned checks. Agent:
`/root/hms_mcp_implementation`. Validation used Linux CPython **3.11.2**, official
MCP SDK **2.3.0**, published HMS Commander **0.3.1**, Pydantic **2.13.5**,
packaging **26.3**, pytest **9.1.1**, and MCP candidate **0.1.0**.

## Completed evidence

- **31 contracts passed** against the actual published HMS 0.3.1 library and the
  candidate adapter. Real basin/met/control/gage fixtures are unmodified selected
  files from the public HMS library. Their origin and SHA-256 values are recorded
  in `tests/fixtures/real-hms/PROVENANCE.json`.
- **39 contracts passed** with the companion local HmsText source: the same 31
  adapter checks plus 8 focused upstream pure text checks on hms/basin/met/control/
  run/gage fixtures. Project/run relationships worked in this source configuration.
  This is unreleased source evidence, not a published package compatibility claim.
- **31 contracts passed** with the built wheel installed into a separate target
  directory. Source modules matched wheel bytes, console entrypoint and dependency
  metadata matched pyproject, and the source distribution included tests/fixture
  provenance. Wheel build, sdist build and wheel rebuild from unpacked sdist passed.
- **One opt-in live official-PyPI metadata check passed**, with no package version
  change. A separate maintenance metadata check confirmed minimum/latest stable
  SDK 2.3.0 and HMS 0.3.1 are currently identical. Ordinary CI does not require live
  network metadata; it covers default-offline, unavailable and update-available
  status without changing installed packages.
- `pip check` passed. No project fixture files were created, removed or altered.
  GIS/Java optional runtime modules were absent from the tested domain read path.

Contracts cover approved field projection, omitted coordinate/geometry attributes,
source hash/root/version provenance, exact control text/time caveats, paging and
SDK-indented character budgets, unsupported fields/types/paths, NUL/oversize
inputs, Unicode, scalar/NaN handling, empty/missing entities, source changes,
leaf/ancestor symlink denial, real worker deadlines/concurrency and cleanup after
allocation failure. Official SDK stdio auto and legacy modes cover tool inventory,
annotations, typed output-schema validation, text/structured equality, bounded
input rejection and recoverable ToolError advice. No engine, GIS, Java, grid,
DSS/HDF/SQLite reader, export or project mutation was invoked.

One discovered issue was corrected: capability reporting now inspects the active
import path without importing HMS, so local/PYTHONPATH HmsText overrides are not
misreported from stale installed RECORD metadata. Windows final-handle identity
is compared lexically to the configured root, without re-resolving mutable paths.

## Logs and artifacts

Full local evidence is in the task workspace's
`implementation/packets/hms_mcp/`: `public-0.3.1-tests.log`,
`local-hmstext-tests.log`, `wheel-tests.log`, `optional-pypi-tests.log`,
`current-pypi-review.json`, `package-evidence.json`, `build.log`,
`sdist-rebuild.log`, `pip-check.log`, and `resolved-versions.txt`.
The JSON evidence records artifact hashes and full wheel metadata. These local
logs are validation records, not fixtures copied into client projects.

## Remaining qualification and release gates

Remote CI passed on Linux Python 3.10.21/3.11.16/3.12.14, minimum and latest-compatible
SDK/domain candidates: 31 passed / 1 optional network skip each, `pip check` and package
builds successful. Native Windows Python 3.11.9 file-policy subset passed 12 tests
with no skips. Windows full-domain reads still require publication of HmsText;
current 0.3.1 Windows reads fail with that prerequisite. The native subset does
not establish full Windows domain adapter or stdio behavior.

The tests establish bounded informational behavior on these fixtures/environments.
They do not establish engineering suitability, universal host activation, or
complete coverage of every HMS format/version. Text-series/report extraction
remains deferred pending dedicated public upstream contracts. The server cannot
attest subagent identity: the host/plugin must enforce tool isolation.

No package publication, deployment or merge was performed. The root coordinator
owns public repository/bootstrap/PR integration.

## Native Windows diagnostic follow-up

The first native Windows policy job stalled; it is not a qualification pass.
Oversized-byte test parameters generated unbounded (>2 MiB) pytest node IDs,
which could overwhelm failure/progress output. IDs are now explicit and bounded.
Native file-policy checks moved to `tests/test_native_policy.py`, which imports
no domain library/adapter, to separate file I/O qualification from library imports.
CI now bounds the Windows test step to 3 minutes and its entire job to 10 minutes,
with verbose unbuffered output and repeating 30 second faulthandler traces starting
before pytest collection. The Linux suite remained 31 passed / 1 optional network skip
after that isolation (`post-windows-diagnostics-linux.log`). These changes improve
diagnostics and bounds; the stalled job's cause remains unconfirmed until native
trace/result evidence is available. No file access controls were weakened.

## Completed native Windows and remote matrix evidence

[GitHub Actions run 37165170753](https://github.com/gpt-cmdr/hms-commander-mcp/actions/runs/37165170753),
source head 8e04b3c: all 7 jobs successful. The Windows job 111326487836 used
Python 3.11.9, pytest 9.1.1, SDK 2.3.0 and HMS 0.3.1. Its 12 tests all passed in 0.07 s
with no skips: 7 path/extension/stream cases, unconfigured root, NUL input, oversized
input, actual approved control text, and native leaf symlink denial. This proves
that subset on that runner; it is not a full Windows domain qualification.

All 6 Linux minimum/latest jobs passed 31 tests and skipped only the opt-in live
network test, then passed `pip check`/build/metadata steps. Resolved SDK 2.3.0 and
HMS 0.3.1 were identical across the two dependency tracks on this date.

Full retrieved logs are `windows-policy-success.log` and
`functional-ci-success.log` in the task packet. Earlier run 37164430236 was
cancelled and its Windows log was not retrievable; no cause is inferred as
confirmed from the successful rerun. No read policy was weakened.
