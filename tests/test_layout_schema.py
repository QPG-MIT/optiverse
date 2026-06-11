"""Drift guard: the canonical `2.0` layout schema (shared with optiverse-web).

The desktop app is the source of the `2.0` project file format. This test pins it
against the same JSON Schema + golden fixture that optiverse-web validates in its
own CI, so the two apps cannot silently diverge. Keep
``schema/optiverse-2.0.schema.json`` and ``tests/fixtures/minimal_layout_2_0.json``
byte-identical to the optiverse-web copies.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SCHEMA = _REPO / "schema" / "optiverse-2.0.schema.json"
_FIXTURE = _REPO / "tests" / "fixtures" / "minimal_layout_2_0.json"
_CONSTANTS = _REPO / "src" / "optiverse" / "core" / "constants.py"


def _file_format_version() -> str:
    """Read FILE_FORMAT_VERSION straight from the (import-free) constants module.

    Loading by file path avoids dragging in the Qt-heavy package import chain, so
    the drift guard runs in any environment that has the source tree.
    """
    spec = importlib.util.spec_from_file_location("optiverse_constants", _CONSTANTS)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FILE_FORMAT_VERSION


def test_file_format_version_matches_schema() -> None:
    schema = json.loads(_SCHEMA.read_text())
    assert schema["properties"]["version"]["const"] == _file_format_version()


def test_golden_fixture_matches_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(
        instance=json.loads(_FIXTURE.read_text()),
        schema=json.loads(_SCHEMA.read_text()),
    )
