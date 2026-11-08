"""Generate GDScript const data tables from the Python character_factory tables.

    uv run python tools/golden/gen_gd_data.py

Output (godot/scripts/core/data/*.gd) is deterministic: Python insertion order,
tabs only, no timestamps. Const GDScript (not JSON) is deliberate so the data
is always part of exports. InventoryItem values are emitted fully expanded
(model_dump shape); consumers must .duplicate(true) them per character.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from storyforge.core import character_factory as cf

OUT = Path(__file__).resolve().parents[2] / "godot" / "scripts" / "core" / "data"

HEADER = (
    "# GENERATED - do not edit by hand.\n"
    "# Source: src/storyforge/core/character_factory.py\n"
    "# Regenerate: uv run python tools/golden/gen_gd_data.py\n"
)


def plain(o: Any) -> Any:
    if hasattr(o, "model_dump"):
        return o.model_dump(mode="json")
    if dataclasses.is_dataclass(o):
        return {f.name: plain(getattr(o, f.name)) for f in dataclasses.fields(o)}
    if isinstance(o, dict):
        return {(k.value if hasattr(k, "value") else k): plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [plain(v) for v in o]
    return o


def lit(o: Any, level: int) -> str:
    pad = "\t" * (level + 1)
    end = "\t" * level
    if o is None:
        return "null"
    if o is True:
        return "true"
    if o is False:
        return "false"
    if isinstance(o, (int, float)):
        return repr(o)
    if isinstance(o, str):
        return json.dumps(o, ensure_ascii=False)
    if isinstance(o, list):
        if not o:
            return "[]"
        if all(isinstance(v, (str, int)) and not isinstance(v, bool) for v in o) and len(json.dumps(o)) < 100:
            return "[" + ", ".join(lit(v, 0) for v in o) + "]"
        return "[\n" + "".join(f"{pad}{lit(v, level + 1)},\n" for v in o) + end + "]"
    if isinstance(o, dict):
        if not o:
            return "{}"
        return "{\n" + "".join(
            f"{pad}{json.dumps(k, ensure_ascii=False)}: {lit(v, level + 1)},\n"
            for k, v in o.items()) + end + "}"
    raise TypeError(type(o))


def write(name: str, doc: str, consts: dict[str, Any]) -> None:
    body = HEADER + f"extends RefCounted\n## {doc}\n\n"
    for cname, value in consts.items():
        body += f"const {cname} := {lit(plain(value), 0)}\n\n"
    (OUT / name).write_text(body.rstrip("\n") + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    write("races_data.gd", "35 race definitions keyed by Race enum value.", {"RACES": cf.RACES})
    write("states_data.gd", "Evolutionary state definitions keyed by enum value.", {"STATES": cf.STATES})
    write("roles_data.gd", "Predator role definitions keyed by enum value.", {"ROLES": cf.ROLES})
    write("backgrounds_data.gd", "Backgrounds and feats (UI/prompt data).",
          {"BACKGROUNDS": cf.BACKGROUNDS, "FEATS": cf.FEATS})
    write("creation_lists_data.gd", "Creation lists and enemy base stats.", {
        "STANDARD_ARRAY": list(cf.STANDARD_ARRAY),
        "SKILLS": cf.SKILLS, "CANTRIPS": cf.CANTRIPS, "ALIGNMENTS": cf.ALIGNMENTS,
        "DIALOGUE_STYLES": cf.DIALOGUE_STYLES,
        "RACE_ENEMY_BASES": {r.value: list(v) for r, v in cf._RACE_ENEMY_BASES.items()},
    })


if __name__ == "__main__":
    main()
