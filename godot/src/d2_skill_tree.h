#ifndef D2_SKILL_TREE_H
#define D2_SKILL_TREE_H

#include <godot_cpp/classes/ref.hpp>
#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/variant/string.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/typed_array.hpp>

using namespace godot;

class D2SkillNode : public RefCounted {
    GDCLASS(D2SkillNode, RefCounted);

private:
    String skill_id;
    String name;
    String description;
    int points_spent = 0;
    int max_points = 5;
    int level_requirement = 1;
    TypedArray<String> prerequisites;

protected:
    static void _bind_methods();

public:
    D2SkillNode();
    ~D2SkillNode();

    void set_skill_id(const String &p_id) { skill_id = p_id; }
    String get_skill_id() const { return skill_id; }

    void set_name(const String &p_name) { name = p_name; }
    String get_name() const { return name; }

    void set_description(const String &p_desc) { description = p_desc; }
    String get_description() const { return description; }

    void set_points_spent(int p_pts) { points_spent = p_pts; }
    int get_points_spent() const { return points_spent; }

    void set_max_points(int p_max) { max_points = p_max; }
    int get_max_points() const { return max_points; }

    void set_level_requirement(int p_req) { level_requirement = p_req; }
    int get_level_requirement() const { return level_requirement; }

    void set_prerequisites(const TypedArray<String> &p_pre) { prerequisites = p_pre; }
    TypedArray<String> get_prerequisites() const { return prerequisites; }
};

class D2SkillTree : public RefCounted {
    GDCLASS(D2SkillTree, RefCounted);

private:
    String class_name;
    Dictionary skills;

protected:
    static void _bind_methods();

public:
    D2SkillTree();
    ~D2SkillTree();

    void set_class_name(const String &p_name) { class_name = p_name; }
    String get_class_name() const { return class_name; }

    void set_skills(const Dictionary &p_skills) { skills = p_skills; }
    Dictionary get_skills() const { return skills; }

    void add_skill_node(const Ref<D2SkillNode> &p_node);
    bool learn_skill(const String &p_id, int p_player_level, int p_unspent_points);
    
    Dictionary serialize() const;
    void deserialize(const Dictionary &p_data);
};

#endif // D2_SKILL_TREE_H
