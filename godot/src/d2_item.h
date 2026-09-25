#ifndef D2_ITEM_H
#define D2_ITEM_H

#include <godot_cpp/classes/ref.hpp>
#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/variant/string.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/typed_array.hpp>

using namespace godot;

class D2Affix : public RefCounted {
    GDCLASS(D2Affix, RefCounted);

private:
    String id;
    String display_name;
    String stat_mod;
    int value = 0;

protected:
    static void _bind_methods();

public:
    D2Affix();
    ~D2Affix();

    void set_id(const String &p_id) { id = p_id; }
    String get_id() const { return id; }

    void set_display_name(const String &p_name) { display_name = p_name; }
    String get_display_name() const { return display_name; }

    void set_stat_mod(const String &p_mod) { stat_mod = p_mod; }
    String get_stat_mod() const { return stat_mod; }

    void set_value(int p_val) { value = p_val; }
    int get_value() const { return value; }
};

class D2Item : public RefCounted {
    GDCLASS(D2Item, RefCounted);

private:
    String name;
    String base_id;
    int rarity = 0; // 0 = Normal, 1 = Magic, 2 = Rare, 3 = Unique
    int base_value = 0;
    int required_level = 1;
    int sockets_max = 0;
    TypedArray<D2Affix> affixes;
    TypedArray<D2Item> socketed_items;

protected:
    static void _bind_methods();

public:
    D2Item();
    ~D2Item();

    void set_name(const String &p_name) { name = p_name; }
    String get_name() const { return name; }

    void set_base_id(const String &p_id) { base_id = p_id; }
    String get_base_id() const { return base_id; }

    void set_rarity(int p_rarity) { rarity = p_rarity; }
    int get_rarity() const { return rarity; }

    void set_base_value(int p_val) { base_value = p_val; }
    int get_base_value() const { return base_value; }

    void set_required_level(int p_lvl) { required_level = p_lvl; }
    int get_required_level() const { return required_level; }

    void set_sockets_max(int p_max) { sockets_max = p_max; }
    int get_sockets_max() const { return sockets_max; }

    void set_affixes(const TypedArray<D2Affix> &p_affixes) { affixes = p_affixes; }
    TypedArray<D2Affix> get_affixes() const { return affixes; }

    void set_socketed_items(const TypedArray<D2Item> &p_items) { socketed_items = p_items; }
    TypedArray<D2Item> get_socketed_items() const { return socketed_items; }

    void add_affix(const Ref<D2Affix> &p_affix);
    void roll_affixes(int p_ilvl);
    
    Dictionary serialize() const;
    void deserialize(const Dictionary &p_data);
};

#endif // D2_ITEM_H
