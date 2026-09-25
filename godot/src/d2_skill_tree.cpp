#include "d2_skill_tree.h"
#include <godot_cpp/core/class_db.hpp>

using namespace godot;

// ─────────────────────── D2SkillNode Implementation ───────────────────────

D2SkillNode::D2SkillNode() {
    // Constructor
}

D2SkillNode::~D2SkillNode() {
    // Destructor
}

void D2SkillNode::_bind_methods() {
    ClassDB::bind_method(D_METHOD("set_skill_id", "skill_id"), &D2SkillNode::set_skill_id);
    ClassDB::bind_method(D_METHOD("get_skill_id"), &D2SkillNode::get_skill_id);
    ClassDB::bind_method(D_METHOD("set_name", "name"), &D2SkillNode::set_name);
    ClassDB::bind_method(D_METHOD("get_name"), &D2SkillNode::get_name);
    ClassDB::bind_method(D_METHOD("set_description", "description"), &D2SkillNode::set_description);
    ClassDB::bind_method(D_METHOD("get_description"), &D2SkillNode::get_description);
    ClassDB::bind_method(D_METHOD("set_points_spent", "points_spent"), &D2SkillNode::set_points_spent);
    ClassDB::bind_method(D_METHOD("get_points_spent"), &D2SkillNode::get_points_spent);
    ClassDB::bind_method(D_METHOD("set_max_points", "max_points"), &D2SkillNode::set_max_points);
    ClassDB::bind_method(D_METHOD("get_max_points"), &D2SkillNode::get_max_points);
    ClassDB::bind_method(D_METHOD("set_level_requirement", "level_requirement"), &D2SkillNode::set_level_requirement);
    ClassDB::bind_method(D_METHOD("get_level_requirement"), &D2SkillNode::get_level_requirement);
    ClassDB::bind_method(D_METHOD("set_prerequisites", "prerequisites"), &D2SkillNode::set_prerequisites);
    ClassDB::bind_method(D_METHOD("get_prerequisites"), &D2SkillNode::get_prerequisites);

    ADD_PROPERTY(PropertyInfo(Variant::STRING, "skill_id"), "set_skill_id", "get_skill_id");
    ADD_PROPERTY(PropertyInfo(Variant::STRING, "name"), "set_name", "get_name");
    ADD_PROPERTY(PropertyInfo(Variant::STRING, "description"), "set_description", "get_description");
    ADD_PROPERTY(PropertyInfo(Variant::INT, "points_spent"), "set_points_spent", "get_points_spent");
    ADD_PROPERTY(PropertyInfo(Variant::INT, "max_points"), "set_max_points", "get_max_points");
    ADD_PROPERTY(PropertyInfo(Variant::INT, "level_requirement"), "set_level_requirement", "get_level_requirement");
    ADD_PROPERTY(PropertyInfo(Variant::ARRAY, "prerequisites", PROPERTY_HINT_NONE, "", PROPERTY_USAGE_DEFAULT, "String"), "set_prerequisites", "get_prerequisites");
}


// ─────────────────────── D2SkillTree Implementation ───────────────────────

D2SkillTree::D2SkillTree() {
    // Constructor
}

D2SkillTree::~D2SkillTree() {
    // Destructor
}

void D2SkillTree::add_skill_node(const Ref<D2SkillNode> &p_node) {
    if (p_node.is_valid()) {
        skills[p_node->get_skill_id()] = p_node;
    }
}

bool D2SkillTree::learn_skill(const String &p_id, int p_player_level, int p_unspent_points) {
    if (!skills.has(p_id)) {
        return false;
    }

    Ref<D2SkillNode> node = skills[p_id];
    if (!node.is_valid()) {
        return false;
    }

    // Check basic points and level requirements
    if (p_unspent_points <= 0 || p_player_level < node->get_level_requirement()) {
        return false;
    }

    // Check max cap
    if (node->get_points_spent() >= node->get_max_points()) {
        return false;
    }

    // Check prerequisites
    TypedArray<String> prereqs = node->get_prerequisites();
    for (int i = 0; i < prereqs.size(); ++i) {
        String pre_id = prereqs[i];
        if (!skills.has(pre_id)) {
            return false;
        }
        Ref<D2SkillNode> pre_node = skills[pre_id];
        if (!pre_node.is_valid() || pre_node->get_points_spent() <= 0) {
            return false;
        }
    }

    // Requirements met, apply learning point
    node->set_points_spent(node->get_points_spent() + 1);
    return true;
}

Dictionary D2SkillTree::serialize() const {
    Dictionary data;
    data["class_name"] = class_name;

    Dictionary skills_data;
    Array keys = skills.keys();
    for (int i = 0; i < keys.size(); ++i) {
        String key = keys[i];
        Ref<D2SkillNode> node = skills[key];
        if (node.is_valid()) {
            Dictionary node_data;
            node_data["skill_id"] = node->get_skill_id();
            node_data["name"] = node->get_name();
            node_data["description"] = node->get_description();
            node_data["points_spent"] = node->get_points_spent();
            node_data["max_points"] = node->get_max_points();
            node_data["level_requirement"] = node->get_level_requirement();
            node_data["prerequisites"] = node->get_prerequisites();
            skills_data[key] = node_data;
        }
    }
    data["skills"] = skills_data;

    return data;
}

void D2SkillTree::deserialize(const Dictionary &p_data) {
    class_name = p_data.get("class_name", "");
    skills.clear();

    Dictionary skills_data = p_data.get("skills", Dictionary());
    Array keys = skills_data.keys();
    for (int i = 0; i < keys.size(); ++i) {
        String key = keys[i];
        Dictionary node_data = skills_data[key];

        Ref<D2SkillNode> node;
        node.instantiate();
        node->set_skill_id(node_data.get("skill_id", ""));
        node->set_name(node_data.get("name", ""));
        node->set_description(node_data.get("description", ""));
        node->set_points_spent(node_data.get("points_spent", 0));
        node->set_max_points(node_data.get("max_points", 5));
        node->set_level_requirement(node_data.get("level_requirement", 1));
        node->set_prerequisites(node_data.get("prerequisites", Array()));

        skills[key] = node;
    }
}

void D2SkillTree::_bind_methods() {
    ClassDB::bind_method(D_METHOD("set_class_name", "class_name"), &D2SkillTree::set_class_name);
    ClassDB::bind_method(D_METHOD("get_class_name"), &D2SkillTree::get_class_name);
    ClassDB::bind_method(D_METHOD("set_skills", "skills"), &D2SkillTree::set_skills);
    ClassDB::bind_method(D_METHOD("get_skills"), &D2SkillTree::get_skills);
    
    ClassDB::bind_method(D_METHOD("add_skill_node", "node"), &D2SkillTree::add_skill_node);
    ClassDB::bind_method(D_METHOD("learn_skill", "id", "player_level", "unspent_points"), &D2SkillTree::learn_skill);
    ClassDB::bind_method(D_METHOD("serialize"), &D2SkillTree::serialize);
    ClassDB::bind_method(D_METHOD("deserialize", "data"), &D2SkillTree::deserialize);

    ADD_PROPERTY(PropertyInfo(Variant::STRING, "class_name"), "set_class_name", "get_class_name");
    ADD_PROPERTY(PropertyInfo(Variant::DICTIONARY, "skills"), "set_skills", "get_skills");
}
