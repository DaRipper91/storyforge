"""Authored quest content kept separate from mutable campaign progress."""

WOLFGUARD_WATCH = "wolfguard_watch"

QUESTS = {
    WOLFGUARD_WATCH: {
        "name": "The Quiet Watch",
        "start_npc_id": "evangeline_wolfholt",
        "turn_in_npc_id": "bryttan_wolfholt",
        "enemy_id": "echo_hound_01",
        "objective": "Defeat the echo hound in Keep Courtyard, then report to Bryttan.",
        "reward_xp": 75,
        "reward_item": {
            "id": "wolfguard_watch_mark",
            "name": "Wolfguard Watch Mark",
            "quantity": 1,
            "equipped": False,
            "value": 0,
            "notes": "A cobalt enamel mark awarded for restoring the courtyard watch.",
            "damage_dice": None,
            "armor_ac_bonus": 0,
        },
    },
}


def quest_for_enemy(enemy_id: str) -> str | None:
    """Return the quest advanced by an enemy defeat, if one is authored."""
    for quest_id, definition in QUESTS.items():
        if definition["enemy_id"] == enemy_id:
            return quest_id
    return None
