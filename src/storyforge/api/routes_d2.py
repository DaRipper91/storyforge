from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import random

from storyforge.api.deps import get_state_manager
from storyforge.core.state_manager import StateManager, StateError
from storyforge.core.models import InventoryItem, CharacterSheet, NarrativeEntry
import datetime as dt

router = APIRouter(prefix="/api/d2", tags=["d2"])

class LearnSkillRequest(BaseModel):
    skill_id: str

# Define static skill templates for Predator Roles
SKILL_TEMPLATES = {
    "stalker": {
        "shadow_strike": {"name": "Shadow Strike", "description": "Deals massive damage from stealth (8s cooldown).", "max_points": 5, "level_requirement": 1, "prerequisites": []},
        "assassinate": {"name": "Assassinate", "description": "Executes low-HP targets (12s cooldown).", "max_points": 5, "level_requirement": 6, "prerequisites": ["shadow_strike"]},
        "speed_of_shadow": {"name": "Speed of Shadow", "description": "Passive: Increases movement speed by 5 per point.", "max_points": 5, "level_requirement": 1, "prerequisites": []}
    },
    "vanguard": {
        "shield_bash": {"name": "Shield Bash", "description": "Stuns a target for 1 round (6s cooldown).", "max_points": 5, "level_requirement": 1, "prerequisites": []},
        "taunt": {"name": "Taunt", "description": "Forces hostile focus and reduces enemy attack bonus (10s cooldown).", "max_points": 5, "level_requirement": 6, "prerequisites": ["shield_bash"]},
        "iron_body": {"name": "Iron Body", "description": "Passive: Increases Armor Class by 1 per 2 points.", "max_points": 5, "level_requirement": 1, "prerequisites": []}
    },
    "catalyst": {
        "explosive_spore": {"name": "Explosive Spore", "description": "Explodes in a 5ft radius dealing fire damage (8s cooldown).", "max_points": 5, "level_requirement": 1, "prerequisites": []},
        "web_trap": {"name": "Web Trap", "description": "Restrains multiple targets on hit (10s cooldown).", "max_points": 5, "level_requirement": 6, "prerequisites": ["explosive_spore"]},
        "toxic_touch": {"name": "Toxic Touch", "description": "Passive: Adds +2 poison damage to all basic attacks per point.", "max_points": 5, "level_requirement": 1, "prerequisites": []}
    },
    "siphoner": {
        "drain_life": {"name": "Drain Life", "description": "Steals lifeforce to heal self and allies (8s cooldown).", "max_points": 5, "level_requirement": 1, "prerequisites": []},
        "spell_steal": {"name": "Spell Steal", "description": "Silences the target's special spells (12s cooldown).", "max_points": 5, "level_requirement": 6, "prerequisites": ["drain_life"]},
        "essence_reserve": {"name": "Essence Reserve", "description": "Passive: Retain 20% of stolen health as a shield.", "max_points": 5, "level_requirement": 1, "prerequisites": []}
    }
}

def initialize_skill_tree(char: CharacterSheet):
    """Lazily initializes the Diablo 2 skill tree on a character sheet if empty."""
    if char.skill_tree:
        return
    
    role = char.predator_role.value.lower()
    templates = SKILL_TEMPLATES.get(role, {})
    
    tree = {}
    for sid, template in templates.items():
        tree[sid] = {
            "skill_id": sid,
            "name": template["name"],
            "description": template["description"],
            "points_spent": 0,
            "max_points": template["max_points"],
            "level_requirement": template["level_requirement"],
            "prerequisites": template["prerequisites"]
        }
    char.skill_tree = tree

@router.post("/character/{char_id}/learn_skill")
async def learn_skill(
    char_id: str,
    req: LearnSkillRequest,
    state: StateManager = Depends(get_state_manager)
) -> dict:
    """Spend a skill point on a specific Diablo 2 style skill node."""
    async with state._lock:
        char = state.current.characters.get(char_id)
        if char is None:
            raise HTTPException(status_code=404, detail=f"Character not found: {char_id}")
        
        initialize_skill_tree(char)
        
        if char.unspent_skill_points <= 0:
            raise HTTPException(status_code=400, detail="No unspent skill points available")
        
        skill = char.skill_tree.get(req.skill_id)
        if skill is None:
            raise HTTPException(status_code=404, detail=f"Skill not found in tree: {req.skill_id}")
        
        if skill["points_spent"] >= skill["max_points"]:
            raise HTTPException(status_code=400, detail="Skill is already maxed out")
        
        if char.level < skill["level_requirement"]:
            raise HTTPException(status_code=400, detail=f"Requires character level {skill['level_requirement']}")
        
        # Check prerequisites
        for prereq_id in skill["prerequisites"]:
            prereq = char.skill_tree.get(prereq_id)
            if prereq is None or prereq["points_spent"] <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Requires at least 1 point in prerequisite skill: {prereq_id}"
                )
        
        # Deduct point and upgrade
        skill["points_spent"] += 1
        char.unspent_skill_points -= 1
        
        # Apply passives immediately if applicable
        if req.skill_id == "speed_of_shadow":
            char.speed = 30 + (skill["points_spent"] * 5)
        elif req.skill_id == "iron_body":
            # Extra AC
            char.armor_class = 10 + (skill["points_spent"] // 2)
            
        summary = {
            "type": "skill_upgraded",
            "character_id": char_id,
            "skill_id": req.skill_id,
            "points_spent": skill["points_spent"],
            "unspent_skill_points": char.unspent_skill_points,
        }
        
        # Record narration
        msg = f"{char.name} spent a skill point on '{skill['name']}' (Rank {skill['points_spent']}/{skill['max_points']})."
        state._state.narrative_log.append(
            NarrativeEntry(
                revision=state._state.revision + 1,
                actor_id=char_id,
                kind="system",
                text=msg,
                timestamp=dt.datetime.now(dt.timezone.utc).isoformat()
            )
        )
        
        await state._commit(summary)
        return summary

@router.post("/character/{char_id}/roll_loot")
async def roll_loot(
    char_id: str,
    rarity_tier: str = "magic",
    state: StateManager = Depends(get_state_manager)
) -> dict:
    """Generate and drop a Diablo 2 style randomized affix item into the inventory."""
    async with state._lock:
        char = state.current.characters.get(char_id)
        if char is None:
            raise HTTPException(status_code=404, detail=f"Character not found: {char_id}")
        
        # Prefix list
        prefixes = [
            {"id": "pre_gleaming", "display_name": "Gleaming", "stat_mod": "hp_max", "value_range": (5, 20)},
            {"id": "pre_sharp", "display_name": "Sharp", "stat_mod": "min_damage", "value_range": (1, 5)},
            {"id": "pre_sturdy", "display_name": "Sturdy", "stat_mod": "armor", "value_range": (1, 4)},
            {"id": "pre_swift", "display_name": "Swift", "stat_mod": "speed", "value_range": (5, 10)}
        ]
        
        # Suffix list
        suffixes = [
            {"id": "suf_life", "display_name": "of Life", "stat_mod": "hp_max", "value_range": (5, 15)},
            {"id": "suf_power", "display_name": "of Power", "stat_mod": "max_damage", "value_range": (2, 8)},
            {"id": "suf_blocking", "display_name": "of Deflection", "stat_mod": "block_chance", "value_range": (2, 6)}
        ]
        
        base_items = [
            {"id": "shortsword", "name": "Shortsword", "val": 15, "dice": "1d6"},
            {"id": "leather_armor", "name": "Leather Armor", "val": 30, "ac": 2},
            {"id": "wooden_shield", "name": "Wooden Shield", "val": 20, "ac": 1, "block": 10},
            {"id": "iron_helmet", "name": "Iron Helmet", "val": 25, "ac": 1}
        ]
        
        base = random.choice(base_items)
        ilvl = char.level
        
        # Roll affixes based on rarity
        rolled_affixes = []
        rarity_tier = rarity_tier.lower()
        if rarity_tier not in ["magic", "rare", "unique"]:
            rarity_tier = "magic"
            
        affixes_count = 1 if rarity_tier == "magic" else 3
        
        chosen_prefixes = set()
        chosen_suffixes = set()
        
        name_prefix = ""
        name_suffix = ""
        
        for _ in range(affixes_count):
            roll_type = random.choice(["prefix", "suffix"])
            if roll_type == "prefix" and len(chosen_prefixes) < len(prefixes):
                pref = random.choice(prefixes)
                while pref["id"] in chosen_prefixes:
                    pref = random.choice(prefixes)
                chosen_prefixes.add(pref["id"])
                val = random.randint(*pref["value_range"]) * ilvl
                rolled_affixes.append({
                    "id": pref["id"],
                    "display_name": pref["display_name"],
                    "stat_mod": pref["stat_mod"],
                    "value": val
                })
                name_prefix = pref["display_name"] + " "
            elif len(chosen_suffixes) < len(suffixes):
                suff = random.choice(suffixes)
                while suff["id"] in chosen_suffixes:
                    suff = random.choice(suffixes)
                chosen_suffixes.add(suff["id"])
                val = random.randint(*suff["value_range"]) * ilvl
                rolled_affixes.append({
                    "id": suff["id"],
                    "display_name": suff["display_name"],
                    "stat_mod": suff["stat_mod"],
                    "value": val
                })
                name_suffix = " " + suff["display_name"]
        
        display_name = f"{name_prefix}{base['name']}{name_suffix}"
        
        # Build item dict
        item_id = f"{base['id']}_{random.randint(100, 999)}"
        item = InventoryItem(
            id=item_id,
            name=display_name,
            quantity=1,
            equipped=False,
            value=base["val"] * ilvl,
            damage_dice=base.get("dice"),
            armor_ac_bonus=base.get("ac", 0),
            
            # Diablo 2 specifics
            rarity=rarity_tier,
            affixes=rolled_affixes,
            sockets_max=random.choice([0, 1, 2]) if rarity_tier != "unique" else 0,
            socketed_items=[],
            required_level=ilvl
        )
        
        char.inventory.append(item)
        
        summary = {
            "type": "loot_rolled",
            "character_id": char_id,
            "item": item.model_dump()
        }
        
        msg = f"{char.name} obtained a {rarity_tier.upper()} item: {display_name}!"
        state._state.narrative_log.append(
            NarrativeEntry(
                revision=state._state.revision + 1,
                actor_id=char_id,
                kind="narration",
                text=msg,
                timestamp=dt.datetime.now(dt.timezone.utc).isoformat()
            )
        )
        
        await state._commit(summary)
        return summary
