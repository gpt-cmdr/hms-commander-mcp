"""Thin public HMS API adapter with an explicit informational field contract."""
from contextlib import redirect_stdout
import hashlib
from importlib import metadata
import math
import os
import sys
from . import __version__
from .contracts import ReadRequest, ReadResult, Section, Source
from .policy import Policy

# Source HMS labels and current public DataFrame keys map to one small output contract.
# Unknown fields are omitted, including all coordinate/canvas/geometry/grid attributes.
FIELD_ALIASES = {
    "Version": "version", "Unit System": "unit_system", "Units": "units",
    "Filename": "filename", "DSS File Name": "dss_file", "DSS File": "dss_file",
    "DSS Pathname": "dss_pathname", "Type": "type", "Data Type": "data_type",
    "Downstream": "downstream", "Area": "area", "LossRate": "loss_method", "Loss": "loss_method",
    "Transform": "transform_method", "Baseflow": "baseflow_method", "Route": "routing_method",
    "Percent Impervious Area": "percent_impervious", "Initial Loss": "initial_loss",
    "Curve Number": "curve_number", "Initial Abstraction": "initial_abstraction",
    "Constant Rate": "constant_rate", "Lag": "lag", "Time of Concentration": "time_of_concentration",
    "Storage Coefficient": "storage_coefficient", "Muskingum K": "muskingum_k", "Muskingum X": "muskingum_x",
    "Precipitation Method": "precipitation_method", "Evapotranspiration Method": "evapotranspiration_method",
    "Snowmelt Method": "snowmelt_method", "Precipitation Gage": "precipitation_gage",
    "Gage": "gage", "Gage Weight": "gage_weight", "Start Date": "start_date", "Start Time": "start_time",
    "End Date": "end_date", "End Time": "end_time", "Time Interval": "time_interval",
    "Time Zone ID": "time_zone_id", "Basin": "basin", "Precip": "met", "Control": "control",
    "Time-Series Output": "time_series_output", "Total Duration": "total_duration",
    "Exceedence Frequency": "exceedance_frequency", "Percent of Duration Before Peak Rainfall": "peak_position_percent",
}
FIELDS = frozenset(FIELD_ALIASES.values())
# Keys already normalized by the current standalone public getters.
FIELD_ALIASES.update({key: key for key in FIELDS})
FIELD_ALIASES["route_method"] = "routing_method"


def _decode(data: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    raise ValueError("Unsupported text encoding")


def _scalar(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if not isinstance(value, (str, int, float, bool)):
        return None
    text = str(value)
    if len(text) > 512:
        raise ValueError("Selected value exceeds the scalar budget; use Python for fuller inspection")
    return text


def _project(section_type: str, name: str, attributes: dict, fields: list[str]) -> Section:
    if len(str(name)) > 256 or len(str(section_type)) > 64:
        raise ValueError("Section identity exceeds the informational budget")
    params = {}
    for key, value in attributes.items():
        canonical = FIELD_ALIASES.get(key)
        if canonical and (not fields or canonical in fields):
            params[canonical] = _scalar(value)
    return Section(section_type=section_type, name=str(name), parameters=params)


def _current_release_rows(data: bytes, kind: str, name: str) -> list[dict]:
    # Current standalone getters accept filenames, not content. A sealed memory
    # snapshot supplies a stable filename without writing a project or temp file.
    if sys.platform != "linux" or not hasattr(os, "memfd_create"):
        raise ValueError("This installed HMS release lacks HmsText; content-based reads require the upstream HmsText release on this platform")
    if kind not in {"basin", "met", "control", "gage"}:
        raise ValueError("Project/run section reads require the upstream public HmsText release; installed 0.3.1 supports bounded basin/met/control/gage reads")
    import fcntl
    from hms_commander import HmsBasin, HmsMet, HmsControl, HmsGage
    fd = os.memfd_create("hms-mcp-text", flags=os.MFD_ALLOW_SEALING | os.MFD_CLOEXEC)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view):]
        os.lseek(fd, 0, os.SEEK_SET)
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL)
        path = f"/proc/self/fd/{fd}"
        rows = []
        if kind == "basin":
            methods = [("Subbasin", HmsBasin.get_subbasins), ("Junction", HmsBasin.get_junctions),
                       ("Reach", HmsBasin.get_reaches), ("Reservoir", HmsBasin.get_reservoirs),
                       ("Source", HmsBasin.get_sources), ("Sink", HmsBasin.get_sinks), ("Diversion", HmsBasin.get_diversions)]
            for section_type, getter in methods:
                for record in getter(path).to_dict("records"):
                    rows.append({"section_type": section_type, "name": record.get("name", ""), "parameters": record})
        elif kind == "met":
            info = HmsMet.get_met_info(path)
            rows.append({"section_type": "Meteorology", "name": name, "parameters": info["meteorology"]})
            for entity, attrs in info["subbasin_assignments"].items():
                rows.append({"section_type": "Subbasin", "name": entity, "parameters": attrs})
        elif kind == "control":
            rows.append({"section_type": "Control", "name": name, "parameters": HmsControl.get_control_info(path)})
        else:
            for record in HmsGage.get_gages(path).to_dict("records"):
                rows.append({"section_type": "Gage", "name": record.get("name", ""), "parameters": record})
        return rows
    finally:
        os.close(fd)


def read_sections(policy: Policy, request: ReadRequest) -> ReadResult:
    unknown = set(request.fields) - FIELDS
    if unknown:
        raise ValueError("Unapproved fields; inspect server_info for the field contract")
    data = policy.read_bytes(request.root, request.file, request.kind)
    text, encoding = _decode(data)
    # Imports run only in this isolated per-request worker. stdout is redirected
    # so domain logging/import messages cannot corrupt the stdio protocol.
    with redirect_stdout(sys.stderr):
        import hms_commander as hms_library
        api = getattr(hms_library, "HmsText", None)
        if api is not None and callable(getattr(api, "parse_sections", None)):
            rows = api.parse_sections(text, request.kind)
            adapter = "HmsText.parse_sections"
            notes = ["Known named sections only; unknown and repeated-key records are not a complete text dump."]
        else:
            from pathlib import Path
            rows = _current_release_rows(data, request.kind, Path(request.file).stem)
            adapter = "published standalone getters, sealed memory snapshot"
            notes = ["Transition adapter: met/control identity uses filename stem, not parsed section name; basin inventory omits detailed parameter blocks."]
    if len(rows) > 10000:
        raise ValueError("Section count exceeds the informational budget; use Python")
    unit_system = next((row["parameters"].get("Unit System") for row in rows if row["parameters"].get("Unit System")), None)
    selected = [row for row in rows if (request.name is None or row["name"] == request.name)
                and (request.section_type is None or row["section_type"] == request.section_type)]
    # Preserve exact source numeric strings through HmsText; legacy getter numbers
    # are normalized by the upstream public API, never rounded by this adapter.
    result = ReadResult(source=Source(root=request.root, file=request.file, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), encoding=encoding),
                        hms_commander_version=metadata.version("hms-commander"), package_version=__version__, mcp_version=metadata.version("mcp"), adapter=adapter, unit_system=unit_system,
                        total=len(selected), returned=0, next_offset=None, truncated=False, rows=[], notes=notes)
    for row in selected[request.offset:request.offset + request.limit]:
        item = _project(row["section_type"], row["name"], row["parameters"], request.fields)
        candidate = result.model_copy(update={"rows": result.rows + [item], "returned": result.returned + 1})
        # Reserve space for pagination metadata added below.
        if len(candidate.model_dump_json(indent=2)) + 128 > request.max_characters:
            break
        result = candidate
    end = request.offset + result.returned
    result.next_offset = end if end < len(selected) else None
    result.truncated = result.next_offset is not None
    if selected[request.offset:] and not result.rows:
        raise ValueError("One row exceeds the output budget; choose fewer fields or use Python")
    if len(result.model_dump_json(indent=2)) > request.max_characters:
        raise ValueError("Envelope exceeds the output budget")
    return result
