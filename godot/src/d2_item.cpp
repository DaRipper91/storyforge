#include "d2_item.h"
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/utility_functions.hpp>
#include <cstdlib>
#include <ctime>

using namespace godot;

// ─────────────────────── D2Affix Implementation ───────────────────────

D2Affix::D2Affix() {
    // Constructor
}

D2Affix::~D2Affix() {
    // Destructor
}

void D2Affix::_bind_methods() {
    ClassDB::bind_method(D_METHOD("set_id", "id"), &D2Affix::set_id);
    ClassDB::bind_method(D_METHOD("get_id"), &D2Affix::get_id);
    ClassDB::bind_method(D_METHOD("set_display_name", "display_name"), &D2Affix::set_display_name);
    ClassDB::bind_method(D_METHOD("get_display_name"), &D2Affix::get_display_name);
    ClassDB::bind_method(D_METHOD("set_stat_mod", "stat_mod"), &D2Affix::set_stat_mod);
    ClassDB::bind_method(D_METHOD("get_stat_mod"), &D2Affix::get_stat_mod);
    ClassDB::bind_method(D_METHOD("set_value", "value"), &D2Affix::set_value);
    ClassDB::bind_method(D_METHOD("get_value"), &D2Affix::get_value);

    ADD_PROPERTY(PropertyInfo(Variant::STRING, "id"), "set_id", "get_id");
    ADD_PROPERTY(PropertyInfo(Variant::STRING, "display_name"), "set_display_name", "get_display_name");
    ADD_PROPERTY(PropertyInfo(Variant::STRING, "stat_mod"), "set_stat_mod", "get_stat_mod");
    ADD_PROPERTY(PropertyInfo(Variant::INT, "value"), "set_value", "get_value");
}


// ─────────────────────── D2Item Implementation ───────────────────────

D2Item::D2Item() {
    // Constructor
}

D2Item::~D2Item() {
    // Destructor
}

void D2Item::add_affix(const Ref<D2Affix> &p_affix) {
    if (p_affix.is_valid()) {
        affixes.append(p_affix);
    }
}

void D2Item::roll_affixes(int p_ilvl) {
    affixes.clear();
    
    if (rarity == 0) { // Normal
        return; 
    }

    // Initialize random seed
    static bool seeded = false;
    if (!seeded) {
        srand(time(nullptr));
        seeded = true;
    }

    struct AffixTemplate {
        const char *id;
        const char *name;
        const char *stat;
        int min_val;
        int max_val;
    };

    AffixTemplate prefix_pool[] = {
        {"pre_gleaming", "Gleaming", "hp_max", 5, 20},
        {"pre_sharp", "Sharp", "min_damage", 1, 5},
        {"pre_sturdy", "Sturdy", "armor", 1, 4},
        {"pre_swift", "Swift", "speed", 5, 10}
    };

    AffixTemplate suffix_pool[] = {
        {"suf_life", "of Life", "hp_max", 5, 15},
        {"suf_power", "of Power", "max_damage", 2, 8},
        {"suf_haste", "of Haste", "attack_speed", 1, 3}, // as simple multiplier value
        {"suf_blocking", "of Deflection", "block_chance", 2, 6}
    };

    int num_prefixes = sizeof(prefix_pool) / sizeof(AffixTemplate);
    int num_suffixes = sizeof(suffix_pool) / sizeof(AffixTemplate);

    int affixes_to_roll = 1;
    if (rarity == 2) { // Rare
        affixes_to_roll = 2 + (rand() % 3); // 2 to 4 affixes
    } else if (rarity == 1) { // Magic
        affixes_to_roll = 1 + (rand() % 2); // 1 to 2 affixes
    }

    bool prefix_chosen[4] = {false};
    bool suffix_chosen[4] = {false};

    for (int i = 0; i < affixes_to_roll; ++i) {
        bool roll_prefix = (rand() % 2 == 0);
        
        if (roll_prefix) {
            int roll = rand() % num_prefixes;
            if (!prefix_chosen[roll]) {
                prefix_chosen[roll] = true;
                Ref<D2Affix> affix;
                affix.instantiate();
                affix->set_id(prefix_pool[roll].id);
                affix->set_display_name(prefix_pool[roll].name);
                affix->set_stat_mod(prefix_pool[roll].stat);
                int val = prefix_pool[roll].min_val + (rand() % (prefix_pool[roll].max_val - prefix_pool[roll].min_val + 1));
                affix->set_value(val * p_ilvl); // Scale with item level
                add_affix(affix);
            }
        } else {
            int roll = rand() % num_suffixes;
            if (!suffix_chosen[roll]) {
                suffix_chosen[roll] = true;
                Ref<D2Affix> affix;
                affix.instantiate();
                affix->set_id(suffix_pool[roll].id);
                affix->set_display_name(suffix_pool[roll].name);
                affix->set_stat_mod(suffix_pool[roll].stat);
                int val = suffix_pool[roll].min_val + (rand() % (suffix_pool[roll].max_val - suffix_pool[roll].min_val + 1));
                affix->set_value(val * p_ilvl);
                add_affix(affix);
            }
        }
    }
}

Dictionary D2Item::serialize() const {
    Dictionary data;
    data["name"] = name;
    data["base_id"] = base_id;
    data["rarity"] = rarity;
    data["base_value"] = base_value;
    data["required_level"] = required_level;
    data["sockets_max"] = sockets_max;

    Array aff_list;
    for (int i = 0; i < affixes.size(); ++i) {
        Ref<D2Affix> aff = affixes[i];
        if (aff.is_valid()) {
            Dictionary aff_data;
            aff_data["id"] = aff->get_id();
            aff_data["display_name"] = aff->get_display_name();
            aff_data["stat_mod"] = aff->get_stat_mod();
            aff_data["value"] = aff->get_value();
            aff_list.append(aff_data);
        }
    }
    data["affixes"] = aff_list;

    Array sock_list;
    for (int i = 0; i < socketed_items.size(); ++i) {
        Ref<D2Item> sock_item = socketed_items[i];
        if (sock_item.is_valid()) {
            sock_list.append(sock_item->serialize());
        }
    }
    data["socketed_items"] = sock_list;

    return data;
}

void D2Item::deserialize(const Dictionary &p_data) {
    name = p_data.get("name", "");
    base_id = p_data.get("base_id", "");
    rarity = p_data.get("rarity", 0);
    base_value = p_data.get("base_value", 0);
    required_level = p_data.get("required_level", 1);
    sockets_max = p_data.get("sockets_max", 0);

    affixes.clear();
    Array aff_list = p_data.get("affixes", Array());
    for (int i = 0; i < aff_list.size(); ++i) {
        Dictionary aff_data = aff_list[i];
        Ref<D2Affix> aff;
        aff.instantiate();
        aff->set_id(aff_data.get("id", ""));
        aff->set_display_name(aff_data.get("display_name", ""));
        aff->set_stat_mod(aff_data.get("stat_mod", ""));
        aff->set_value(aff_data.get("value", 0));
        add_affix(aff);
    }

    socketed_items.clear();
    Array sock_list = p_data.get("socketed_items", Array());
    for (int i = 0; i < sock_list.size(); ++i) {
        Dictionary sock_data = sock_list[i];
        Ref<D2Item> sock_item;
        sock_item.instantiate();
        sock_item->deserialize(sock_data);
        socketed_items.append(sock_item);
    }
}

void D2Item::_bind_methods() {
    ClassDB::bind_method(D_METHOD("set_name", "name"), &D2Item::set_name);
    ClassDB::bind_method(D_METHOD("get_name"), &D2Item::get_name);
    ClassDB::bind_method(D_METHOD("set_base_id", "base_id"), &D2Item::set_base_id);
    ClassDB::bind_method(D_METHOD("get_base_id"), &D2Item::get_base_id);
    ClassDB::bind_method(D_METHOD("set_rarity", "rarity"), &D2Item::set_rarity);
    ClassDB::bind_method(D_METHOD("get_rarity"), &D2Item::get_rarity);
    ClassDB::bind_method(D_METHOD("set_base_value", "base_value"), &D2Item::set_base_value);
    ClassDB::bind_method(D_METHOD("get_base_value"), &D2Item::get_base_value);
    ClassDB::bind_method(D_METHOD("set_required_level", "required_level"), &D2Item::set_required_level);
    ClassDB::bind_method(D_METHOD("get_required_level"), &D2Item::get_required_level);
    ClassDB::bind_method(D_METHOD("set_sockets_max", "sockets_max"), &D2Item::set_sockets_max);
    ClassDB::bind_method(D_METHOD("get_sockets_max"), &D2Item::get_sockets_max);
    ClassDB::bind_method(D_METHOD("set_affixes", "affixes"), &D2Item::set_affixes);
    ClassDB::bind_method(D_METHOD("get_affixes"), &D2Item::get_affixes);
    ClassDB::bind_method(D_METHOD("set_socketed_items", "socketed_items"), &D2Item::set_socketed_items);
    ClassDB::bind_method(D_METHOD("get_socketed_items"), &D2Item::get_socketed_items);
    
    ClassDB::bind_method(D_METHOD("add_affix", "affix"), &D2Item::add_affix);
    ClassDB::bind_method(D_METHOD("roll_affixes", "ilvl"), &D2Item::roll_affixes);
    ClassDB::bind_method(D_METHOD("serialize"), &D2Item::serialize);
    ClassDB::bind_method(D_METHOD("deserialize", "data"), &D2Item::deserialize);

    ADD_PROPERTY(PropertyInfo(Variant::STRING, "name"), "set_name", "get_name");
    ADD_PROPERTY(PropertyInfo(Variant::STRING, "base_id"), "set_base_id", "get_base_id");
    ADD_PROPERTY(PropertyInfo(Variant::INT, "rarity"), "set_rarity", "get_rarity");
    ADD_PROPERTY(PropertyInfo(Variant::INT, "base_value"), "set_base_value", "get_base_value");
    ADD_PROPERTY(PropertyInfo(Variant::INT, "required_level"), "set_required_level", "get_required_level");
    ADD_PROPERTY(PropertyInfo(Variant::INT, "sockets_max"), "set_sockets_max", "get_sockets_max");
    ADD_PROPERTY(PropertyInfo(Variant::ARRAY, "affixes", PROPERTY_HINT_NONE, "", PROPERTY_USAGE_DEFAULT, "D2Affix"), "set_affixes", "get_affixes");
    ADD_PROPERTY(PropertyInfo(Variant::ARRAY, "socketed_items", PROPERTY_HINT_NONE, "", PROPERTY_USAGE_DEFAULT, "D2Item"), "set_socketed_items", "get_socketed_items");
}
