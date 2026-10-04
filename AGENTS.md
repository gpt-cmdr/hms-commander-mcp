# HMS Commander MCP agent contract

This repository owns a constrained informational server. Preserve read-only,
low-dependency, non-spatial/non-gridded output and subagent-only client routing.
Only explicit typed tools are registered. Do not reflect the domain library into
MCP. Do not add model execution, setters, cloning, exports, downloads, generic
file/SQL/code readers, geometry, DSS/HDF/SQLite or gridded data. Use public HMS
library APIs; domain parsers remain upstream. No global project state.

Read README.md and COMPATIBILITY.md before changes. Keep stdout for MCP wire
traffic, logs on stderr, configured roots enforced, and byte/row/character/time
limits enforced with explicit counts/truncation. Per-request objects and workers
must not retain a prior project's state. Do not accept terms or infer suitability
from successful parsing. Annotations and client roots are not access controls.

HEC is primary for documented HEC-HMS methods and terminology. State supported
project capabilities and reproducible observations directly, with their scope.
Maintain an objective independent third-party voice and passive official HEC
references. Repository editorial standards do not apply to users' external work.

Dependency update PRs need minimum/latest contract and wheel/sdist evidence.
Preserve user pins; no runtime pip install, unattended merge/publish, or dependency
range widening without qualification. Do not run tests, model engines or user
project processing unless the task authorizes that work.
