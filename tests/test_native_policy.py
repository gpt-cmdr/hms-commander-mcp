"""Native secure-file policy qualification; imports no domain library or adapter."""
import os
from pathlib import Path
import pytest
from hms_commander_mcp.policy import MAX_FILE_BYTES, Policy

FIXTURE = Path(__file__).parent / "fixtures" / "real-hms"

@pytest.mark.parametrize("relative,kind", [("../outside.control", "control"), ("/outside.control", "control"),
                                          ("model.dss", "control"), ("model.sqlite", "control"), ("model.hdf", "control"),
                                          ("model.grid", "control"), ("model.control:stream", "control")])
def test_paths_and_extensions_denied(tmp_path, relative, kind):
    with pytest.raises((ValueError, OSError)):
        Policy([str(tmp_path)]).read_bytes(str(tmp_path.resolve()), relative, kind)


def test_root_identity_denied(tmp_path):
    with pytest.raises(ValueError, match="not configured"):
        Policy([str(FIXTURE)]).read_bytes(str(tmp_path), "x.control", "control")


@pytest.mark.parametrize("payload", [b"Control: x\n\x00End:\n", b"a" * (MAX_FILE_BYTES + 1)], ids=["nul-input", "oversized-input"])
def test_binary_and_size_denied(tmp_path, payload):
    (tmp_path / "x.control").write_bytes(payload)
    with pytest.raises(ValueError):
        Policy([str(tmp_path)]).read_bytes(str(tmp_path.resolve()), "x.control", "control")


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

