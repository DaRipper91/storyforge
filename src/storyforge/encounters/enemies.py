"""
Enemy combat logic — pure functions, no I/O.

One round of combat:
  1. Player attacks enemy (d20 + best STR/DEX mod + proficiency)
  2. If hit → damage; if enemy survives → enemy counterattacks
  3. Returns AttackResult for both sides so the route can build narrative

Dice notation: "2d6+2", "1d8", "1d4-1" (clamped to min 1 when negative).
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass

from storyforge.core.models import CharacterSheet, EnemySheet


@dataclass
class AttackResult:
    hit: bool
    roll: int            # raw d20
    total: int           # roll + bonus
    damage: int
    attacker_name: str
    target_name: str
    hint: str            # short phrase fed to Gemini for narration context


def _roll_dice(notation: str) -> int:
    """Parse and roll e.g. '2d6+2', '1d8', '1d4'."""
    m = re.match(r"(\d+)d(\d+)([+-]\d+)?", notation.strip())
    if not m:
        return 1
    count, sides = int(m.group(1)), int(m.group(2))
    bonus = int(m.group(3) or 0)
    return max(1, sum(random.randint(1, sides) for _ in range(count)) + bonus)


def _mod(score: int) -> int:
    return (score - 10) // 2


def _weapon_dice(char: CharacterSheet) -> str:
    """Return the damage dice of the first equipped weapon, else default 1d6."""
    for item in char.inventory:
        if item.equipped and item.damage_dice:
            return item.damage_dice
    return "1d6"


def resolve_player_attack(attacker: CharacterSheet, target: EnemySheet) -> AttackResult:
    best_mod = max(_mod(attacker.abilities.STR), _mod(attacker.abilities.DEX))
    bonus = best_mod + attacker.proficiency_bonus
    roll = random.randint(1, 20)
    total = roll + bonus
    crit = roll == 20
    hit = crit or total >= target.armor_class

    if hit:
        dice = _weapon_dice(attacker)
        dmg_roll = _roll_dice(dice) + max(best_mod, 0)
        if crit:
            dmg_roll += _roll_dice(dice)   # crit: roll weapon dice twice
        damage = max(1, dmg_roll)
    else:
        damage = 0

    if crit:
        hint = f"{attacker.name} scores a critical hit on {target.name} for {damage} damage!"
    elif hit:
        hint = f"{attacker.name} hits {target.name} for {damage} damage."
    else:
        hint = f"{attacker.name} swings at {target.name} but misses (rolled {total} vs AC {target.armor_class})."

    return AttackResult(
        hit=hit, roll=roll, total=total, damage=damage,
        attacker_name=attacker.name, target_name=target.name, hint=hint,
    )


def resolve_enemy_attack(enemy: EnemySheet, target: CharacterSheet) -> AttackResult:
    roll = random.randint(1, 20)
    total = roll + enemy.attack_bonus
    hit = roll == 20 or total >= target.armor_class
    damage = _roll_dice(enemy.damage_dice) if hit else 0

    if hit:
        hint = f"{enemy.name} strikes back at {target.name} for {damage} damage!"
    else:
        hint = f"{enemy.name} lunges at {target.name} but can't connect."

    return AttackResult(
        hit=hit, roll=roll, total=total, damage=damage,
        attacker_name=enemy.name, target_name=target.name, hint=hint,
    )
