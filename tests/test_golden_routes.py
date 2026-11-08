"""
Replay every route-level golden flow against the real FastAPI app.

Flows live in tests/golden/routes/<flow>.json and are produced by
tools/golden/record_routes.py (format: tests/golden/ROUTES_README.md).
Two checks, same pattern as tests/test_golden.py:

* replay  - re-run each committed flow's recorded requests + RNG script and
            assert the whole document (responses, bus events, state) is equal;
* re-record - rebuild every flow from the recorder's definitions and assert the
            bytes equal the committed files (so fixtures cannot go stale).
"""
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_FIXTURES = _ROOT / "tests" / "golden" / "routes"
sys.path.insert(0, str(_ROOT / "tools" / "golden"))

import record_routes as rr  # noqa: E402

_FILES = sorted(_FIXTURES.glob("*.json"))
_EXPECTED_FLOWS = {
    "boot_reads", "lobby_slots", "character_creation", "exploration",
    "enemy_combat", "world_travel", "campaigns", "paradox_time",
}


def test_flows_present():
    assert {p.stem for p in _FILES} == _EXPECTED_FLOWS, \
        "route fixtures missing; run tools/golden/record_routes.py"


@pytest.mark.parametrize("path", _FILES, ids=[p.stem for p in _FILES])
def test_route_flow_replay(path: Path):
    doc = json.loads(path.read_text())
    assert doc["format"] == rr.FORMAT and doc["flow"] == path.stem
    got = rr.replay(doc)
    assert got == doc


def test_rerecord_is_byte_identical():
    fresh = rr.build_all()
    assert set(fresh) == {p.name for p in _FILES}
    for p in _FILES:
        assert fresh[p.name] == p.read_text(), f"{p.name} is stale; re-run the recorder"
