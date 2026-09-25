#ifndef D2_COMBAT_H
#define D2_COMBAT_H

#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/variant/string.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/array.hpp>
#include "d2_item.h"

using namespace godot;

class D2CombatEngine : public RefCounted {
    GDCLASS(D2CombatEngine, RefCounted);

private:
    Dictionary skill_cooldowns; // maps skill_id to remaining cooldown float
    float faster_cast_rate = 0.0f; // 0.0 to 1.0 modifier
    float faster_hit_recovery = 0.0f;

protected:
    static void _bind_methods();

public:
    D2CombatEngine();
    ~D2CombatEngine();

    void set_faster_cast_rate(float p_fcr) { faster_cast_rate = p_fcr; }
    float get_faster_cast_rate() const { return faster_cast_rate; }

    void set_faster_hit_recovery(float p_fhr) { faster_hit_recovery = p_fhr; }
    float get_faster_hit_recovery() const { return faster_hit_recovery; }

    // D2 Roll Mechanics
    int calculate_damage(int p_min_dmg, int p_max_dmg, int p_stat_bonus, bool p_is_crit);
    bool check_block(int p_dexterity, int p_shield_block_chance, int p_player_level);
    
    // Cooldown management
    void update_cooldowns(float p_delta);
    bool is_skill_ready(const String &p_skill_id);
    void trigger_cooldown(const String &p_skill_id, float p_base_cooldown);

    // Elite Monster Affixes
    Dictionary roll_elite_modifiers(int p_count);
    Dictionary apply_elite_affixes(const Dictionary &p_base_stats, const Array &p_modifiers);
};

#endif // D2_COMBAT_H
