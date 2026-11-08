"""
Replay every golden fixture against the Python implementation.

Fixtures live in tests/golden/fixtures/<module>/<case>.json and are produced
by tools/golden/record_fixtures.py (see tests/golden/README.md). A GDScript
runner replays the same files against the port.
"""
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_FIXTURES = _ROOT / "tests" / "golden" / "fixtures"
sys.path.insert(0, str(_ROOT / "tools" / "golden"))

import golden_lib as gl  # noqa: E402

_FILES = sorted(_FIXTURES.rglob("*.json"))


def _ids() -> list[str]:
    return [str(p.relative_to(_FIXTURES).with_suffix("")) for p in _FILES]


def _norm(o):
    return json.loads(json.dumps(o))


def test_fixtures_present():
    assert len(_FILES) > 300, "golden fixtures missing; run tools/golden/record_fixtures.py"
    assert {p.parent.name for p in _FILES} == {
        "character_factory", "enemies", "grid", "rules", "state_manager", "validators"}


@pytest.mark.parametrize("path", _FILES, ids=_ids())
def test_golden_fixture(path: Path):
    fx = json.loads(path.read_text())
    assert path.stem == fx["case"] and path.parent.name == fx["module"]
    outcome, rng = gl.run_case(fx["module"], fx["function"], fx["inputs"], fx["rng_script"])

    # RNG script must be consumed exactly, with the recorded bounds.
    assert rng.leftover() == {}, "rng_script not fully consumed"
    assert rng.randint_bounds == fx["rng_script"]["randint_bounds"]

    expected = fx["expected"]
    if isinstance(expected, dict) and set(expected) == {"raises", "message_contains"}:
        assert outcome.get("raises") == expected["raises"], outcome
        assert expected["message_contains"] in outcome["message"]
    else:
        assert "expected" in outcome, outcome
        assert _norm(outcome["expected"]) == expected


def test_recorder_is_deterministic_and_current():
    """Re-recording yields exactly the committed bytes (no stale/missing files)."""
    import record_fixtures as rec

    first = rec.build_all()
    second = rec.build_all()
    assert first == second
    on_disk = {str(p.relative_to(_FIXTURES)): p.read_text() for p in _FILES}
    assert first == on_disk
