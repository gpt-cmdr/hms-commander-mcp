"""Contracts use unmodified published-repository text fixtures; no engines/binaries."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import pytest
from hms_commander_mcp.adapter import FIELDS, _scalar, read_sections
from hms_commander_mcp.contracts import ReadRequest, ReadResult
from hms_commander_mcp.policy import MAX_FILE_BYTES, Policy
from hms_commander_mcp import worker

FIXTURE = Path(__file__).parent / "fixtures" / "real-hms"
import hms_commander
PURE_API = (os.environ.get("HMS_MCP_EXPECT_HMSTEXT") == "1" if "HMS_MCP_EXPECT_HMSTEXT" in os.environ
            else hasattr(hms_commander, "HmsText"))


def request(file="Control_5.control", **kwargs):
    return ReadRequest(root=str(FIXTURE.resolve()), file=file, kind=Path(file).suffix[1:], **kwargs)


def fingerprint(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("file", ["A100_1PCT.basin", "1__24HR.met", "Control_5.control", "A1000000.gage"])
def test_real_public_getters_read_only(file):
    before = fingerprint(FIXTURE)
    result = worker.bounded_read(Policy([str(FIXTURE)]), request(file, limit=3))
    assert result.returned and result.returned <= 3
    assert result.source.sha256 == hashlib.sha256((FIXTURE / file).read_bytes()).hexdigest()
    assert result.source.root == str(FIXTURE.resolve())
    assert result.hms_commander_version and result.mcp_version and result.package_version
    assert all(set(row.parameters) <= FIELDS for row in result.rows)
    assert all(not {"canvas_x", "canvas_y", "latitude", "longitude", "geometry", "grid"} & set(row.parameters) for row in result.rows)
    assert fingerprint(FIXTURE) == before
    assert (result.adapter == "HmsText.parse_sections") == PURE_API


@pytest.mark.parametrize("file", ["A1000000.hms", "A1000000.run"])
def test_project_run_api_prerequisite(file):
    if PURE_API:
        result = worker.bounded_read(Policy([str(FIXTURE)]), request(file))
        assert result.rows and result.adapter == "HmsText.parse_sections"
        if file.endswith(".run"):
            assert any("basin" in row.parameters and "control" in row.parameters for row in result.rows)
    else:
        with pytest.raises(ValueError, match="require"):
            worker.bounded_read(Policy([str(FIXTURE)]), request(file))


def test_control_source_spelling_and_time_caveat():
    result = read_sections(Policy([str(FIXTURE)]), request(fields=["start_date", "start_time", "time_interval"]))
    assert result.rows[0].parameters == {"start_date": "31 May 2007", "start_time": "24:00", "time_interval": "5"}
    assert "no timezone or interval units inferred" in result.time_basis


def test_paging_and_character_budget():
    policy = Policy([str(FIXTURE)])
    first = read_sections(policy, request("A100_1PCT.basin", limit=100, max_characters=2048))
    assert first.truncated and first.next_offset == first.returned and first.returned < first.total
    assert len(first.model_dump_json(indent=2)) <= 2048
    second = read_sections(policy, request("A100_1PCT.basin", limit=1, offset=first.next_offset))
    assert second.rows[0].name not in {r.name for r in first.rows}
    assert first.source.sha256 == second.source.sha256


def test_unknown_fields_rejected():
    with pytest.raises(ValueError, match="Unapproved fields"):
        read_sections(Policy([str(FIXTURE)]), request(fields=["latitude"]))


@pytest.mark.parametrize("relative,kind", [("../outside.control", "control"), ("/outside.control", "control"),
                                          ("model.dss", "control"), ("model.sqlite", "control"), ("model.hdf", "control"),
                                          ("model.grid", "control"), ("model.control:stream", "control")])
def test_paths_and_extensions_denied(tmp_path, relative, kind):
    with pytest.raises((ValueError, OSError)):
        Policy([str(tmp_path)]).read_bytes(str(tmp_path.resolve()), relative, kind)


def test_root_identity_denied(tmp_path):
    with pytest.raises(ValueError, match="not configured"):
        Policy([str(FIXTURE)]).read_bytes(str(tmp_path), "x.control", "control")


def test_symlink_and_root_ancestor_denied(tmp_path):
    if os.name != "posix":
        pytest.skip("POSIX no-follow directory-descriptor behavior")
    outside = tmp_path / "outside"; outside.mkdir(); (outside / "x.control").write_text("Control: x\nEnd:\n")
    root = tmp_path / "parent" / "root"; root.mkdir(parents=True)
    policy = Policy([str(root)])
    (root / "link.control").symlink_to(outside / "x.control")
    with pytest.raises(OSError):
        policy.read_bytes(str(root), "link.control", "control")
    original = tmp_path / "original"; (tmp_path / "parent").rename(original)
    (tmp_path / "parent").symlink_to(outside, target_is_directory=True)
    with pytest.raises(OSError):
        policy.read_bytes(str(root), "x.control", "control")


@pytest.mark.parametrize("payload", [b"Control: x\n\x00End:\n", b"a" * (MAX_FILE_BYTES + 1)])
def test_binary_and_size_denied(tmp_path, payload):
    (tmp_path / "x.control").write_bytes(payload)
    with pytest.raises(ValueError):
        Policy([str(tmp_path)]).read_bytes(str(tmp_path.resolve()), "x.control", "control")


def test_encoding_unicode_and_scalars(tmp_path):
    path = tmp_path / "unicode.control"
    path.write_text("Control: Étude\n     Units: м³/с\n     Start Time: 24:00\n     Canvas X: 1.25\nEnd:\n", encoding="utf-8")
    result = read_sections(Policy([str(tmp_path)]), ReadRequest(root=str(tmp_path.resolve()), file=path.name, kind="control"))
    assert result.rows[0].parameters["units"] == "м³/с"
    assert "canvas_x" not in result.rows[0].parameters
    assert _scalar(float("nan")) is None and _scalar(float("inf")) is None
    import numpy as np
    assert _scalar(np.int64(7)) == "7"
    with pytest.raises(ValueError, match="scalar budget"):
        _scalar("x" * 513)


def test_missing_empty_and_name_selection(tmp_path):
    policy = Policy([str(tmp_path)])
    with pytest.raises(FileNotFoundError):
        policy.read_bytes(str(tmp_path.resolve()), "missing.control", "control")
    (tmp_path / "empty.control").write_text("")
    result = read_sections(policy, ReadRequest(root=str(tmp_path.resolve()), file="empty.control", kind="control", name="missing"))
    assert result.total == result.returned == 0 and result.next_offset is None


def _slow_reader(connection, roots, payload):
    time.sleep(5)


def test_worker_timeout_concurrency_and_allocation_cleanup(monkeypatch):
    monkeypatch.setattr(worker, "_child", _slow_reader)
    start = time.monotonic()
    with pytest.raises(ValueError, match="time budget"):
        worker.bounded_read(Policy([str(FIXTURE)]), request(timeout_seconds=1))
    assert time.monotonic() - start < 4
    assert worker.SLOTS.acquire(blocking=False)
    assert worker.SLOTS.acquire(blocking=False)
    try:
        with pytest.raises(ValueError, match="busy"):
            worker.bounded_read(Policy([str(FIXTURE)]), request())
    finally:
        worker.SLOTS.release(); worker.SLOTS.release()
    class BrokenContext:
        def Pipe(self, **kwargs):
            raise OSError("allocation denied")
    monkeypatch.setattr(worker.multiprocessing, "get_context", lambda *args: BrokenContext())
    with pytest.raises(OSError):
        worker.bounded_read(Policy([str(FIXTURE)]), request())
    assert worker.SLOTS.acquire(blocking=False)
    assert worker.SLOTS.acquire(blocking=False)
    worker.SLOTS.release(); worker.SLOTS.release()


def test_version_check_offline_preserves_pins(monkeypatch):
    from mcp.client import Client
    from hms_commander_mcp.server import create_server
    before = fingerprint(FIXTURE)
    import hms_commander_mcp.server as module
    monkeypatch.setattr(module, "bounded_version_check", lambda: (False, "offline"))
    async def run():
        async with Client(create_server(Policy([str(FIXTURE)]))) as client:
            result = await client.call_tool("server_info", {"check_updates": True})
            assert not result.is_error
            info = result.structured_content
            assert info["update_status"] == "unavailable" and info["update_notes"] == ["offline"]
            assert info["hms_commander_version"]
    asyncio.run(run())
    assert fingerprint(FIXTURE) == before


@pytest.mark.parametrize("mode", ["auto", "legacy"])
def test_official_sdk_stdio_schema_result_error(mode):
    from mcp.client import Client
    from mcp.client.stdio import StdioServerParameters
    from jsonschema import validate
    before = fingerprint(FIXTURE)
    async def run():
        transport = StdioServerParameters(command=sys.executable, args=["-m", "hms_commander_mcp", "--root", str(FIXTURE.resolve())], env=dict(os.environ))
        async with Client(transport, mode=mode) as client:
            tools = (await client.list_tools()).tools
            assert {tool.name for tool in tools} == {"server_info", "read_hms_sections"}
            info_tool = next(tool for tool in tools if tool.name == "server_info")
            read_tool = next(tool for tool in tools if tool.name == "read_hms_sections")
            assert info_tool.annotations.open_world_hint is True
            assert read_tool.annotations.read_only_hint is True and read_tool.annotations.open_world_hint is False
            good = await client.call_tool("read_hms_sections", {"request": request().model_dump()})
            assert not good.is_error and good.structured_content
            validate(good.structured_content, read_tool.output_schema)
            ReadResult.model_validate(good.structured_content)
            assert json.loads(good.content[0].text) == good.structured_content
            bad = await client.call_tool("read_hms_sections", {"request": request(fields=["geometry"]).model_dump()})
            assert bad.is_error and "Unapproved fields" in bad.content[0].text
            bounded = await client.call_tool("read_hms_sections", {"request": {**request().model_dump(), "limit": 999}})
            assert bounded.is_error
            info = await client.call_tool("server_info", {})
            assert info.structured_content["update_status"] == "not_checked"
    asyncio.run(run())
    assert fingerprint(FIXTURE) == before


def test_stable_snapshot_rejects_changed_source(tmp_path, monkeypatch):
    if os.name != "posix":
        pytest.skip("Windows reader denies concurrent write sharing instead")
    import hms_commander_mcp.policy as policy_module
    file = tmp_path / "changing.control"
    file.write_text("Control: original\nEnd:\n")
    original_read = policy_module.os.read
    changed = False
    def changing_read(fd, count):
        nonlocal changed
        chunk = original_read(fd, count)
        if not changed:
            file.write_text("Control: changed-source\nEnd:\n")
            changed = True
        return chunk
    monkeypatch.setattr(policy_module.os, "read", changing_read)
    with pytest.raises(ValueError, match="changed while reading"):
        Policy([str(tmp_path)]).read_bytes(str(tmp_path.resolve()), file.name, "control")


def test_status_default_no_network_and_version_update(monkeypatch):
    from mcp.client import Client
    import hms_commander_mcp.server as module
    from importlib import metadata
    from packaging.version import Version
    initial = {p: metadata.version(p) for p in ("mcp", "hms-commander", "hms-commander-mcp")}
    def denied():
        raise AssertionError("default status must not query a network")
    monkeypatch.setattr(module, "bounded_version_check", denied)
    async def run():
        async with Client(module.create_server(Policy([str(FIXTURE)]))) as client:
            status = await client.call_tool("server_info", {})
            assert not status.is_error and status.structured_content["update_status"] == "not_checked"
            assert status.structured_content["pure_text_api"] == PURE_API
            monkeypatch.setattr(module, "bounded_version_check", lambda: (True, {"mcp": "999.0", "hms-commander": "999.0"}))
            updated = await client.call_tool("server_info", {"check_updates": True})
            assert updated.structured_content["update_status"] == "update_available"
            assert updated.structured_content["latest_hms_version"] == "999.0"
    asyncio.run(run())
    assert initial == {p: metadata.version(p) for p in initial}


def test_no_optional_gis_java_engine_modules():
    # Library base imports are permitted; optional runtimes must stay lazy.
    assert not any(name in sys.modules for name in ("jnius", "rasterio", "geopandas", "pyproj", "osgeo"))


def test_policy_native_known_text():
    data = Policy([str(FIXTURE)]).read_bytes(str(FIXTURE.resolve()), "Control_5.control", "control")
    assert data == (FIXTURE / "Control_5.control").read_bytes()


def test_policy_leaf_link_native(tmp_path):
    outside = tmp_path / "outside.control"; outside.write_text("Control: x\nEnd:\n")
    root = tmp_path / "root"; root.mkdir()
    try:
        (root / "link.control").symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"Host lacks native link privilege: {exc}")
    with pytest.raises((ValueError, OSError)):
        Policy([str(root)]).read_bytes(str(root.resolve()), "link.control", "control")


@pytest.mark.skipif(os.environ.get("HMS_MCP_CHECK_NETWORK") != "1", reason="Explicit optional official-PyPI network qualification")
def test_optional_real_pypi_metadata():
    from importlib import metadata
    before = {p: metadata.version(p) for p in ("mcp", "hms-commander")}
    ok, payload = worker.bounded_version_check()
    assert ok, payload
    assert payload["mcp"] and payload["hms-commander"]
    assert before == {p: metadata.version(p) for p in before}
