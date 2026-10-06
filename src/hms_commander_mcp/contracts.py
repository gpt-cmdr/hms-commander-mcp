"""Typed informational contracts, independent of domain-library imports."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class ReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    root: str = Field(min_length=1, max_length=1024, description="Exact configured project root.")
    file: str = Field(min_length=1, max_length=512, description="Relative approved HMS text file; references are not followed.")
    kind: Literal["hms", "basin", "met", "control", "run", "gage"]
    name: str | None = Field(default=None, max_length=256, description="Exact named section, or omit for a bounded inventory.")
    section_type: str | None = Field(default=None, max_length=64)
    fields: list[str] = Field(default_factory=list, max_length=16, description="Approved canonical field names; empty selects known fields.")
    offset: int = Field(default=0, ge=0, le=10000)
    limit: int = Field(default=20, ge=1, le=100)
    max_characters: int = Field(default=8000, ge=2048, le=16000)
    timeout_seconds: float = Field(default=15, ge=1, le=30)

class Section(BaseModel):
    section_type: str
    name: str
    parameters: dict[str, str | None]

class Source(BaseModel):
    root: str
    file: str
    sha256: str
    bytes: int
    encoding: str

class ReadResult(BaseModel):
    source: Source
    hms_commander_version: str
    package_version: str
    mcp_version: str
    adapter: str
    unit_system: str | None = None
    time_basis: str = "Source text; no timezone or interval units inferred."
    total: int
    returned: int
    next_offset: int | None
    truncated: bool
    rows: list[Section]
    notes: list[str]

class ServerInfo(BaseModel):
    package_version: str
    hms_commander_version: str
    mcp_version: str
    platform: str
    pure_text_api: bool
    latest_package_version: str | None = None
    latest_hms_version: str | None = None
    latest_mcp_version: str | None = None
    update_status: str = "not_checked"
    update_notes: list[str] = Field(default_factory=list)
    current_release_transition_available: bool
    tools: list[str]
    fields: list[str]
    limits: dict[str, int]
    boundary: str
