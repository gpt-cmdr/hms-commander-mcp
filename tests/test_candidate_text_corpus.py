"""Synthetic independent source-value oracles for the upstream content API.

These records contain no private project names or model parameters. Full domain
stdio checks require HmsText; the published Linux transition is tested separately.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import pytest
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters
from jsonschema import validate
import hms_commander

pytestmark = pytest.mark.skipif(not hasattr(hms_commander, "HmsText"), reason="Candidate HmsText content API is not installed")

# Literal source data and independently declared expected output, not generated
# through the production parser or field alias table.
CASES = {
    "hms": ("Project: étude\n     Version: 4.14\n     Unit System: Metric\nEnd:\nBasin: basin α\n     Filename: missing.basin\nEnd:\n", [("Project", "étude", {"version": "4.14", "unit_system": "Metric"}), ("Basin", "basin α", {"filename": "missing.basin"})]),
    "basin": ("Basin: basin α\n     Unit System: English\nEnd:\nSubbasin: S α\n     Area: 1.250000\n     Downstream: R β\n     LossRate: SCS\n     Curve Number: 77.123400\n     Canvas X: 999999\n     Canvas Y: 888888\nEnd:\nReach: R β\n     Route: Muskingum\n     Muskingum K: 0.025000\n     Muskingum X: 0.200000\nEnd:\n", [("Basin", "basin α", {"unit_system": "English"}), ("Subbasin", "S α", {"area": "1.250000", "downstream": "R β", "loss_method": "SCS", "curve_number": "77.123400"}), ("Reach", "R β", {"routing_method": "Muskingum", "muskingum_k": "0.025000", "muskingum_x": "0.200000"})]),
    "met": ("Meteorology: storm α\n     Precipitation Method: Specified Hyetograph\n     Evapotranspiration Method: None\nEnd:\nSubbasin: S α\n     Precipitation Gage: gage β\n     Latitude: 999999\nEnd:\n", [("Meteorology", "storm α", {"precipitation_method": "Specified Hyetograph", "evapotranspiration_method": "None"}), ("Subbasin", "S α", {"precipitation_gage": "gage β"})]),
    "control": ("Control: event α\n     Start Date: 31 December 2020\n     Start Time: 24:00\n     End Date: 2 January 2021\n     End Time: 00:00\n     Time Interval: 5\n     Time Interval: 15\nEnd:\n", [("Control", "event α", {"start_date": "31 December 2020", "start_time": "24:00", "end_date": "2 January 2021", "end_time": "00:00", "time_interval": "15"})]),
    "run": ("Run: run α\n     Basin: basin α\n     Precip: storm α\n     Control: event α\n     Time-Series Output: True\nEnd:\n", [("Run", "run α", {"basin": "basin α", "met": "storm α", "control": "event α", "time_series_output": "True"})]),
    "gage": ("Precipitation Gage: gage β\n     Units: м³/с\n     DSS File: missing.dss\n     DSS Pathname: /A/B/C/D/E/F/\n     Longitude: 999999\nEnd:\n", [("Precipitation Gage", "gage β", {"units": "м³/с", "dss_file": "missing.dss", "dss_pathname": "/A/B/C/D/E/F/"})]),
}


def fingerprint(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("mode", ["auto", "legacy"])
def test_all_six_kinds_sdk_independent_source_oracle(tmp_path, mode):
    for kind, (text, expected) in CASES.items():
        (tmp_path / f"record.{kind}").write_text(text, encoding="utf-8")
    # An instruction-like value in an excluded description remains source data.
    (tmp_path / "empty.control").write_text("")
    before = fingerprint(tmp_path)

    async def exercise():
        transport = StdioServerParameters(command=sys.executable, args=["-m", "hms_commander_mcp", "--root", str(tmp_path)], env=dict(os.environ))
        async with Client(transport, mode=mode) as client:
            tools = (await client.list_tools()).tools
            read_tool = next(tool for tool in tools if tool.name == "read_hms_sections")
            assert read_tool.annotations.read_only_hint and not read_tool.annotations.open_world_hint
            info = await client.call_tool("server_info", {})
            assert not info.is_error and info.structured_content["pure_text_api"]
            for kind, (_, expected) in CASES.items():
                request = {"root": str(tmp_path), "file": f"record.{kind}", "kind": kind, "limit": 100, "max_characters": 16000}
                response = await client.call_tool("read_hms_sections", {"request": request})
                assert not response.is_error, response.content
                out = response.structured_content
                validate(out, read_tool.output_schema)
                assert json.loads(response.content[0].text) == out
                assert len(response.content[0].text) <= 16000
                assert out["adapter"] == "HmsText.parse_sections"
                assert out["source"]["sha256"] == before[f"record.{kind}"]
                actual = [(row["section_type"], row["name"], row["parameters"]) for row in out["rows"]]
                assert actual == expected
                assert out["returned"] == out["total"] == len(expected) and not out["truncated"]
                assert "no timezone or interval units inferred" in out["time_basis"]
                for typ, name, values in expected:
                    fields = list(values)[:1]
                    selected = await client.call_tool("read_hms_sections", {"request": {**request, "name": name, "section_type": typ, "fields": fields, "limit": 1}})
                    assert not selected.is_error
                    rows = selected.structured_content["rows"]
                    assert len(rows) == 1 and rows[0]["name"] == name
                    assert rows[0]["parameters"] == {field: values[field] for field in fields}
                first = await client.call_tool("read_hms_sections", {"request": {**request, "limit": 1}})
                assert first.structured_content["next_offset"] == (1 if len(expected) > 1 else None)
                if len(expected) > 1:
                    second = await client.call_tool("read_hms_sections", {"request": {**request, "offset": 1, "limit": 1}})
                    assert second.structured_content["rows"][0]["name"] == expected[1][1]
                    assert second.structured_content["source"]["sha256"] == out["source"]["sha256"]
            empty = await client.call_tool("read_hms_sections", {"request": {"root": str(tmp_path), "file": "empty.control", "kind": "control"}})
            assert not empty.is_error and empty.structured_content["total"] == 0
            denied = await client.call_tool("read_hms_sections", {"request": {"root": str(tmp_path), "file": "record.basin", "kind": "basin", "fields": ["latitude"]}})
            assert denied.is_error
            # Missing referenced basin/DSS paths did not prevent these reads and
            # no target, sidecar, output, cache, or log file appeared in the root.
            assert not (await client.call_tool("server_info", {})).is_error

    asyncio.run(exercise())
    assert fingerprint(tmp_path) == before
