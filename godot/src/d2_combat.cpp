#include "d2_combat.h"
#include <godot_cpp/core/class_db.hpp>
#include <cstdlib>
#include <algorithm>

using namespace godot;

D2CombatEngine::D2CombatEngine() {
    // Constructor
}

D2CombatEngine::~D2CombatEngine() {
    // Destructor
}

int D2CombatEngine::calculate_damage(int p_min_dmg, int p_max_dmg, int p_stat_bonus, bool p_is_crit) {
    if (p_max_dmg <= p_min_dmg) {
        p_max_dmg = p_min_dmg + 1;
    }
    int raw = p_min_dmg + (rand() % (p_max_dmg - p_min_dmg + 1));
    int damage = raw + p_stat_bonus;
    if (p_is_crit) {
        damage *= 2;
    }
    return std::max(1, damage);
}

bool D2CombatEngine::check_block(int p_dexterity, int p_shield_block_chance, int p_player_level) {
    if (p_player_level <= 0) {
        p_player_level = 1;
    }
    // Diablo 2 Block Formula: Block % = (Shield Block % * (Dexterity - 15)) / (Player Level * 2)
    int calculated = (p_shield_block_chance * (p_dexterity - 15)) / (p_player_level * 2);
    // Hard cap at 75% like D2
    int block_pct = std::min(75, std::max(0, calculated));
    return (rand() % 100) < block_pct;
}

void D2CombatEngine::update_cooldowns(float p_delta) {
    Array keys = skill_cooldowns.keys();
    for (int i = 0; i < keys.size(); ++i) {
        String key = keys[i];
        float val = skill_cooldowns[key];
        val -= p_delta;
        if (val <= 0.0f) {
            skill_cooldowns.erase(key);
        } else {
            skill_cooldowns[key] = val;
        }
    }
}

bool D2CombatEngine::is_skill_ready(const String &p_skill_id) {
    if (!skill_cooldowns.has(p_skill_id)) {
        return true;
    }
    float val = skill_cooldowns[p_skill_id];
    return val <= 0.0f;
}

void D2CombatEngine::trigger_cooldown(const String &p_skill_id, float p_base_cooldown) {
    // Apply Faster Cast Rate (FCR) reduction to cooldowns
    float actual = p_base_cooldown * (1.0f - std::min(0.75f, faster_cast_rate));
    skill_cooldowns[p_skill_id] = actual;
}

Dictionary D2CombatEngine::roll_elite_modifiers(int p_count) {
    Dictionary result;
    const char *affix_pool[] = {
        "Cold Enchanted",
        "Lightning Enchanted",
        "Fire Enchanted",
        "Mana Burn",
        "Extra Fast",
        "Stone Skin",
        "Teleportation",
        "Multiple Shots"
    };
    int pool_size = sizeof(affix_pool) / sizeof(const char *);
    
    Array rolled;
    bool chosen[8] = {false};
    
    int count = std::min(p_count, pool_size);
    for (int i = 0; i < count; ++i) {
        int idx = rand() % pool_size;
        while (chosen[idx]) {
            idx = (idx + 1) % pool_size;
        }
        chosen[idx] = true;
        rolled.append(String(affix_pool[idx]));
    }
    result["modifiers"] = rolled;
    return result;
}

Dictionary D2CombatEngine::apply_elite_affixes(const Dictionary &p_base_stats, const Array &p_modifiers) {
    Dictionary stats = p_base_stats.duplicate();
    
    // Elites get 400% HP boost by default
    int hp = stats.get("hp_max", 100);
    hp *= 4;
    stats["hp_max"] = hp;
    stats["hp_current"] = hp;

    // 150% base damage boost
    int min_dmg = stats.get("min_damage", 10);
    int max_dmg = stats.get("max_damage", 20);
    stats["min_damage"] = (int)(min_dmg * 1.5f);
    stats["max_damage"] = (int)(max_dmg * 1.5f);

    for (int i = 0; i < p_modifiers.size(); ++i) {
        String mod = p_modifiers[i];
        if (mod == "Extra Fast") {
            int speed = stats.get("speed", 30);
            stats["speed"] = (int)(speed * 1.4f);
        } else if (mod == "Stone Skin") {
            int ac = stats.get("armor_class", 10);
            stats["armor_class"] = ac + 4; // Flat +4 bonus to AC
        } else if (mod == "Fire Enchanted") {
            stats["fire_damage_bonus"] = 5; // Add extra fire damage
        } else if (mod == "Cold Enchanted") {
            stats["cold_damage_bonus"] = 5;
        } else if (mod == "Lightning Enchanted") {
            stats["lightning_damage_bonus"] = 5;
        }
    }

    return stats;
}

void D2CombatEngine::_bind_methods() {
    ClassDB::bind_method(D_METHOD("set_faster_cast_rate", "fcr"), &D2CombatEngine::set_faster_cast_rate);
    ClassDB::bind_method(D_METHOD("get_faster_cast_rate"), &D2CombatEngine::get_faster_cast_rate);
    ClassDB::bind_method(D_METHOD("set_faster_hit_recovery", "fhr"), &D2CombatEngine::set_faster_hit_recovery);
    ClassDB::bind_method(D_METHOD("get_faster_hit_recovery"), &D2CombatEngine::get_faster_hit_recovery);
    
    ClassDB::bind_method(D_METHOD("calculate_damage", "min_dmg", "max_dmg", "stat_bonus", "is_crit"), &D2CombatEngine::calculate_damage);
    ClassDB::bind_method(D_METHOD("check_block", "dexterity", "shield_block_chance", "player_level"), &D2CombatEngine::check_block);
    ClassDB::bind_method(D_METHOD("update_cooldowns", "delta"), &D2CombatEngine::update_cooldowns);
    ClassDB::bind_method(D_METHOD("is_skill_ready", "skill_id"), &D2CombatEngine::is_skill_ready);
    ClassDB::bind_method(D_METHOD("trigger_cooldown", "skill_id", "base_cooldown"), &D2CombatEngine::trigger_cooldown);
    ClassDB::bind_method(D_METHOD("roll_elite_modifiers", "count"), &D2CombatEngine::roll_elite_modifiers);
    ClassDB::bind_method(D_METHOD("apply_elite_affixes", "base_stats", "modifiers"), &D2CombatEngine::apply_elite_affixes);

    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "faster_cast_rate"), "set_faster_cast_rate", "get_faster_cast_rate");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "faster_hit_recovery"), "set_faster_hit_recovery", "get_faster_hit_recovery");
}
