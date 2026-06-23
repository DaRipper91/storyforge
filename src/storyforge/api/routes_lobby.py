"""
Lobby + character creation routes.

Endpoints:
    POST /api/lobby/join      — claim a slot with a controller ID
    POST /api/lobby/leave     — release a slot
    POST /api/character/create — finalize a slot into a CharacterSheet
    POST /api/lobby/start     — transition to EXPLORATION
    GET  /api/lobby/catalog   — race + class definitions for the UI
"""
from __future__ import annotations
import asyncio
import io
import logging
import os
from PIL import Image
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
import jwt

from storyforge.config import settings
from storyforge.api.deps import get_state_manager
from storyforge.ai.client import gemini_client

logger = logging.getLogger(__name__)
from storyforge.core.character_factory import (
    RACES, STATES, ROLES, BACKGROUNDS, FEATS, SKILLS, CANTRIPS, ALIGNMENTS, DIALOGUE_STYLES,
)
from storyforge.core.models import CharacterCreationRequest, TurnPhase
from storyforge.core.state_manager import StateError, StateManager


router = APIRouter(prefix="/api", tags=["lobby"])


# ───────────────────────── Request models ─────────────────────────

class SetPhaseRequest(BaseModel):
    phase: TurnPhase


class JoinRequest(BaseModel):
    # If authenticated, this is ignored and the Google ID is used.
    controller_id: str | None = Field(default=None, min_length=1, max_length=200)


class LeaveRequest(BaseModel):
    controller_id: str | None = Field(default=None, min_length=1, max_length=200)


class UpdateNameRequest(BaseModel):
    slot_index: int = Field(ge=0, le=3)
    name: str = Field(min_length=0, max_length=24)
    controller_id: str | None = Field(default=None, min_length=1, max_length=200)


class SaveDraftRequest(BaseModel):
    controller_id: str = Field(min_length=1, max_length=200)
    # Only the fields that change at each step are sent
    creation_step: str | None = None
    race: str | None = None
    evolution_state: str | None = None
    predator_role: str | None = None
    starting_era: str | None = None
    assigned_abilities: dict | None = None
    equipment_choice_id: str | None = None
    background: str | None = None
    skill_proficiencies: list[str] | None = None
    feat: str | None = None
    cantrips: list[str] | None = None
    alignment: str | None = None
    pronouns: str | None = None
    title: str | None = None
    dialogue_style: str | None = None
    physical_description: str | None = None
    backstory: str | None = None
    personality_traits: str | None = None
    flaws: str | None = None
    bonds: str | None = None
    ideals: str | None = None
    keepsake_name: str | None = None


# ───────────────────────── Endpoints ─────────────────────────

@router.get("/lobby/catalog")
async def get_catalog() -> dict:
    """Static reference data for the creation UI. Cached client-side."""
    return {
        "races": {
            race.value: {
                "name": rdef.name,
                "speed": rdef.speed,
                "ability_bonuses": rdef.ability_bonuses,
                "flavor": rdef.flavor,
                "group": rdef.group,
                "before": rdef.before,
            }
            for race, rdef in RACES.items()
        },
        "states": {
            state.value: {
                "name": sdef.name,
                "hit_die": sdef.hit_die,
                "base_armor_class": sdef.base_armor_class,
                "flavor": sdef.flavor,
            }
            for state, sdef in STATES.items()
        },
        "roles": {
            role.value: {
                "name": pdef.name,
                "primary_item": pdef.primary_item.model_dump(mode="json"),
                "equipment_choices": [
                    item.model_dump(mode="json") for item in pdef.equipment_choices
                ],
                "flavor": pdef.flavor,
            }
            for role, pdef in ROLES.items()
        },
        "backgrounds": {
            key: {
                "name": bdef.name,
                "flavor": bdef.flavor,
                "perk_name": bdef.perk_name,
                "perk_description": bdef.perk_description,
                "bonus_skills": list(bdef.bonus_skills),
                "skill_pool": list(bdef.skill_pool),
            }
            for key, bdef in BACKGROUNDS.items()
        },
        "feats": {
            key: {
                "name": fdef.name,
                "flavor": fdef.flavor,
                "mechanical_effect": fdef.mechanical_effect,
            }
            for key, fdef in FEATS.items()
        },
        "skills": SKILLS,
        "cantrips": CANTRIPS,
        "alignments": ALIGNMENTS,
        "dialogue_styles": DIALOGUE_STYLES,
        "standard_array": [15, 14, 13, 12, 10, 8],
    }


@router.post("/lobby/join")
async def join_lobby(
    req: JoinRequest,
    state: StateManager = Depends(get_state_manager),
    request: Request = None,
) -> dict:
    # Use Google ID if available, else fallback to provided controller_id (e.g. guest/local)
    token = request.cookies.get("storyforge_session")
    controller_id = req.controller_id
    
    if token:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            controller_id = f"google::{payload['sub']}"
        except Exception:
            pass

    if not controller_id:
        raise HTTPException(status_code=401, detail="Authentication or controller_id required")

    try:
        return await state.claim_slot(controller_id=controller_id)
    except StateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/lobby/leave")
async def leave_lobby(
    req: LeaveRequest,
    state: StateManager = Depends(get_state_manager),
    request: Request = None,
) -> dict:
    token = request.cookies.get("storyforge_session")
    controller_id = req.controller_id

    if token:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            controller_id = f"google::{payload['sub']}"
        except Exception:
            pass

    if not controller_id:
        raise HTTPException(status_code=401, detail="Authentication or controller_id required")

    try:
        return await state.release_slot(controller_id=controller_id)
    except StateError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/lobby/update_name")
async def update_name(
    req: UpdateNameRequest,
    state: StateManager = Depends(get_state_manager),
    request: Request = None,
) -> dict:
    token = request.cookies.get("storyforge_session")
    controller_id = req.controller_id

    if token:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            controller_id = f"google::{payload['sub']}"
        except Exception:
            pass

    if not controller_id:
        raise HTTPException(status_code=401, detail="Authentication or controller_id required")

    try:
        return await state.update_slot_name(
            slot_index=req.slot_index,
            name=req.name,
            controller_id=controller_id,
        )
    except StateError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/lobby/save_draft")
async def save_draft(
    req: SaveDraftRequest,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    patch = {k: v for k, v in req.model_dump().items() if k != "controller_id" and v is not None}
    try:
        return await state.save_draft(controller_id=req.controller_id, patch=patch)
    except StateError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/lobby/set_phase")
async def set_phase(
    req: SetPhaseRequest,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    try:
        return await state.set_phase(req.phase)
    except StateError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/character/create")
async def create_character(
    req: CharacterCreationRequest,
    state: StateManager = Depends(get_state_manager),
) -> dict:
    try:
        return await state.create_character(req)
    except (StateError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/lobby/start")
async def start_game(
    state: StateManager = Depends(get_state_manager),
) -> dict:
    try:
        return await state.start_exploration()
    except StateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


class GeneratePortraitRequest(BaseModel):
    prompt: str
    race: str


RACE_VISUAL_BLUEPRINTS: dict[str, str] = {
    # Cosmic
    "voidwraith": "A tall stellar scavenger entity standing in a dark void. Its body is entirely composed of swirling violet cosmic dust, a crackling purple nebula energy core, and the visible, glowing skeletal system of a dead planet. Wide cinematic framing, sharp neon edge highlights.",
    "nullshade": "A formless, shadowy hunter stalking out from a pitch-black interdimensional rift. A translucent dark matter body with faint starlight eyes and glowing sharp edges. Surreal cosmic horror aesthetic, blue ambient light.",
    "ironlocust": "A biomechanical swarm humanoid with a jagged, metallic chitinous exoskeleton. Swarming particles of rust drift off its frame, displaying sharp mandibles and iridescent insectoid wings that reflect harsh neon lighting. Gritty cyberpunk style.",
    "embervein": "A massive, towering leviathan creature with cracked, dark obsidian stone skin. Molten magma and glowing white-hot lava pulse violently through its veins like an active planetary core. Intense heat distortion.",
    "riftwalker": "A slender, phase-shifting cyberpunk ninja hunter partially fading out of reality. Translucent blue and violet speed trails, with faint neon grid lines tracing its shifting silhouette in a stealthy posture.",
    # Primal
    "solarlord": "A majestic celestial avian humanoid riding an intense beam of solid sunlight. Feathers made of pure white and gold solar flares, eyes burning like miniature stars. Blinding celestial lighting.",
    "thornmimic": "A sinister shapeshifter with a body composed of dark, ancient tree bark and tangled gnarled vines. Part of its face shifts cleanly into a hollow wooden mask with glowing emerald eyes.",
    "cinderkin": "A small, nimble crystalline fire-sprite forged entirely from jagged volcanic glass. A core of pure crimson flame burns bright inside its translucent body, casting floating sparks in a dark volcanic cavern.",
    "deeptyrant": "A massive, terrifying cephalopodic alien mind sitting on an abyssal stone throne. Bioluminescent neon blue and green markings glow along its heavy tentacles. Set in the dark, lightless ocean depths with an eerie cosmic horror style.",
    "grimcrow": "An ominous humanoid oracle completely covered in obsidian-black feathers. Holding a gnarled staff of glowing white bone bound tightly with raw, stolen purple magic runes.",
    # Eldritch
    "bloodweaver": "A regal, terrifying horror entity with long, sharp tendrils of crystallized crimson blood spinning gracefully around its fingers. Elegant but monstrous silhouette, gothic cyberpunk aesthetic, sinister royal atmosphere.",
    "dreamhusk": "A haunting, spore-borne entity made of pale fungal mycelium and glowing mushrooms. Its face constantly shifts, projecting a hazy, tragic illusion of a deceased human face. Dark surrealism, eerie atmosphere.",
    "bonedrifter": "A horrific parasitic skeletal being where a pale, calcified exoskeleton forms an external bone cage around a trapped, hollow host shadow. Body-horror mutation.",
    "mindspider": "A large, translucent arachnid humanoid with a glowing, highly visible nervous system and an exposed crystalline brain. Harvesting glowing purple memory strands, cyberpunk psychic horror style.",
    "chaosling": "A twitching, distorted entity made of unraveled fragments of reality and glitched neon code, roughly stitched together into borrowed human flesh. Glitch-art, reality warping, unsettling dark sci-fi aesthetic.",
    # Mechanical
    "ironveil": "An ultra-thin, gossamer-sleek metallic war construct. Its body consists of razor-sharp geometric plates resembling origami metal, folding flat to slip through a glowing wireframe wall. High-tech cyberpunk stealth design.",
    "forgespawn": "A shifting humanoid organism made entirely of reflective liquid chrome and molten iron. One arm morphs dynamically into a jagged blade structure against a high-tech industrial foundry background.",
    "cinderplate": "A heavy, massive mech-suit built from blackened, scorched iron plating over a highly visible, white-hot molten core. Heavy steam and sparks vent from back-mounted exhaust ports. Industrial cyberpunk war machine.",
    "hexgear": "A modular, six-sided robotic construct made of interlinked hexagonal metallic plates. Shifting its geometry mid-action into a dynamic combat stance. Hard-surface sci-fi design, high technical detail.",
    "wirewraith": "A terrifying synthetic construct with no outer armor plating, revealing thousands of glowing, exposed neon-blue nerve cables and fiber-optic wires pulsing with data and electrical arcs. Cyberpunk body horror.",
    # Humanoid
    "ashenborn": "A post-apocalyptic human survivor with completely charred, ash-black skin that cracks to reveal an inner, furious fire. Entirely fireproof, holding a weapon, gritty post-apocalyptic style.",
    "hollowsong": "A gaunt, dark-elven figure with pale hair whose silver tattoos glow in reverse, literally absorbing and dimming the ambient magical light around them. Anti-magic aura, moody dark fantasy.",
    "veilborn": "A sleek dark elf completely adapted to absolute silence and pitch darkness. Charcoal skin, blind but glowing white eyes, wearing sound-dampening cyberpunk leather gear.",
    "thornweft": "A wood elf who has physically merged with the forest. Thick, gnarled tree bark grows seamlessly over their shoulders and cheeks, leaves and roots interwoven with their hair, druidic dark fantasy.",
    "ashcrown": "A regal, traditional high elf who refuses to change, but their body is becoming brittle and semi-translucent like frosted glass. Wearing cracked gold armor, tragic decaying royalty aesthetic.",
    "ironfast": "A dense, heavily built dwarf whose skin and bones have calcified into dark, indestructible granite stone. Slower, immovable stance, runic engravings carved into stone skin.",
    "coreborn": "A deep-dwelling dwarf with charcoal skin, whose eyes burn with a malicious, abyssal purple void energy pulled up from the deepest core of the earth, subterranean horror.",
    "warpbred": "A massive, hulking orc warrior whose flesh has been mutated and amplified by an unstable magical paradox. Asymmetrical muscle growth, glowing neon veins, savage cyberpunk barbarian.",
    "splitblood": "A half-orc character whose body is visually split or asymmetric, representing a constant chaotic negotiation between human and orc physiology. Scarred, hybrid armor, intense expressions.",
    "duskweft": "A halfling rogue slipping sideways out of reality. Half of their body is solid, while the other half dissolves into a smoky, blurred shadow silhouette, ethereal phantom thief style.",
    "glitchkin": "A short gnome tinkerer whose body is half-fleshy and half-cybernetic, with internal micro-drones and nanites visibly self-repairing a damaged mechanical arm, terminal user aesthetic.",
    "fractureline": "A half-elf character literally split down the center of their design: one side wears pristine old-world classical fantasy armor, while the other side is scarred, rugged, and dressed in post-apocalyptic survival gear.",
    "emberpact": "A rogue tiefling with broken, smoking horns. Demonic fire dances around their hands free of any infernal leashes or contracts, rebellious cyberpunk-fantasy hybrid.",
    "fallenlight": "An aasimar warrior whose divine wings are burnt to ash and cinder. They still emit a cold, faint neon glow, but their face reflects utter isolation from the gods, dark fallen angel aesthetic.",
    "scaleworn": "A powerful dragonborn whose draconic scales are collapsing inward, turning into a dense, dark reptilian armor plating. Smoke venting from nostrils, heavy combat stance, dark fantasy."
}


@router.post("/character/generate_portrait")
async def generate_portrait(req: GeneratePortraitRequest) -> dict:
    prompt = req.prompt
    race = req.race.lower().replace(" ", "").replace("_", "").replace("-", "")
    
    if not race:
        raise HTTPException(status_code=400, detail="Race is required")
        
    try:
        base_desc = RACE_VISUAL_BLUEPRINTS.get(race, f"A {req.race} creature.")
        
        # Merge the baseline blueprint with the user's custom details
        styled_prompt = (
            f"Dark apocalyptic cyberpunk-fantasy tabletop miniature style, front facing portrait of a {req.race}. "
            f"{base_desc} "
        )
        if prompt.strip():
            styled_prompt += f"Custom details: {prompt}. "
        styled_prompt += (
            "Solid black background, concept art illustration, high resolution, "
            "3d render look, centered framing, alpha cutout friendly."
        )
        
        logger.info(f"Generating portrait for race {race} with prompt: {styled_prompt}")
        
        response = await asyncio.to_thread(
            gemini_client.client.models.generate_images,
            model='imagen-3.0-generate-002',
            prompt=styled_prompt,
            config=dict(
                number_of_images=1,
                output_mime_type="image/png",
                aspect_ratio="1:1"
            )
        )
        if not response.generated_images:
            raise ValueError("No images returned from Imagen")
            
        img_bytes = response.generated_images[0].image.image_bytes
        
        char_dir = "/home/daripper/Projects/storyforge/godot/assets/characters"
        os.makedirs(char_dir, exist_ok=True)
        png_path = os.path.join(char_dir, f"{race}.png")
        
        with open(png_path, "wb") as f:
            f.write(img_bytes)
            
        # Process standee OBJ/MTL
        im = Image.open(io.BytesIO(img_bytes))
        if im.mode != 'RGBA':
            im = im.convert('RGBA')
            
        alpha = im.getchannel('A')
        bbox = alpha.getbbox()
        if bbox is not None:
            cropped_im = im.crop(bbox)
            cropped_name = f"{race}_cropped.png"
            cropped_path = os.path.join(char_dir, cropped_name)
            cropped_im.save(cropped_path)
            
            w, h = cropped_im.size
            aspect_ratio = float(w) / float(h)
            STAND_HEIGHT = 1.6
            STAND_DEPTH = 0.06
            stand_width = aspect_ratio * STAND_HEIGHT
            
            model_dir = "/home/daripper/Projects/storyforge/godot/assets/models/player"
            os.makedirs(model_dir, exist_ok=True)
            obj_path = os.path.join(model_dir, f"{race}.obj")
            
            half_w = stand_width / 2.0
            half_d = STAND_DEPTH / 2.0
            
            vertices = [
                (-half_w, 0.0, half_d),
                (half_w, 0.0, half_d),
                (half_w, STAND_HEIGHT, half_d),
                (-half_w, STAND_HEIGHT, half_d),
                (-half_w, 0.0, -half_d),
                (half_w, 0.0, -half_d),
                (half_w, STAND_HEIGHT, -half_d),
                (-half_w, STAND_HEIGHT, -half_d)
            ]
            
            uvs = [
                (0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.5, 0.5)
            ]
            
            normals = [
                (0.0, 0.0, 1.0), (0.0, 0.0, -1.0), (-1.0, 0.0, 0.0),
                (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, -1.0, 0.0)
            ]
            
            with open(obj_path, "w") as f:
                f.write(f"# 3D Standee cutout for {race}\n")
                f.write(f"mtllib {race}.mtl\n\n")
                for v in vertices:
                    f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
                f.write("\n")
                for uv in uvs:
                    f.write(f"vt {uv[0]:.6f} {uv[1]:.6f}\n")
                f.write("\n")
                for n in normals:
                    f.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")
                f.write("\n")
                f.write("usemtl CharacterMaterial\n")
                f.write("f 1/1/1 2/2/1 3/3/1 4/4/1\n")
                f.write("f 6/2/2 5/1/2 8/4/2 7/3/2\n")
                f.write("f 5/5/3 1/5/3 4/5/3 8/5/3\n")
                f.write("f 2/5/4 6/5/4 7/5/4 3/5/4\n")
                f.write("f 4/5/5 3/5/5 7/5/5 8/5/5\n")
                f.write("f 5/5/6 6/5/6 2/5/6 1/5/6\n")
                
            mtl_path = os.path.join(model_dir, f"{race}.mtl")
            with open(mtl_path, "w") as f:
                f.write("# Material library\n")
                f.write("newmtl CharacterMaterial\n")
                f.write("Ka 1.0 1.0 1.0\n")
                f.write("Kd 1.0 1.0 1.0\n")
                f.write("Ks 0.0 0.0 0.0\n")
                f.write("d 1.0\n")
                f.write("illum 1\n")
                f.write(f"map_Kd ../../characters/{race}_cropped.png\n")
                
        return {"status": "success", "message": f"Portrait generated for {race}"}
        
    except Exception as exc:
        logger.error(f"Failed to generate portrait: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
