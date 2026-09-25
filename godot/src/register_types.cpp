#include "register_types.h"

#include <gdextension_interface.h>
#include <godot_cpp/core/defs.hpp>
#include <godot_cpp/godot.hpp>

// Include our custom C++ headers
#include "d2_item.h"
#include "d2_skill_tree.h"
#include "d2_combat.h"

using namespace godot;

void initialize_d2_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }

    // Register our C++ classes to Godot's ClassDB
    ClassDB::register_class<D2Affix>();
    ClassDB::register_class<D2Item>();
    ClassDB::register_class<D2SkillNode>();
    ClassDB::register_class<D2SkillTree>();
    ClassDB::register_class<D2CombatEngine>();
}

void uninitialize_d2_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
}

extern "C" {
// Initialization function matching entry_symbol in storyforge.gdextension
GDExtensionBool GDE_EXPORT d2_engine_init(GDExtensionInterfaceGetProcAddress p_get_proc_address, GDExtensionClassLibraryPtr p_library, GDExtensionInitialization *r_initialization) {
    godot::GDExtensionBinding::InitObject init_obj(p_get_proc_address, p_library, r_initialization);

    init_obj.register_initializer(initialize_d2_module);
    init_obj.register_terminator(uninitialize_d2_module);
    init_obj.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_SCENE);

    return init_obj.init();
}
}
