# GEMINI.md

This file provides guidance to Gemini CLI when working with code in this repository.
Refer to CLAUDE.md for full architecture, commands, and project structure.

---

## Incident Log

### 2026-05-20 — Race Rename Incident

**What happened:**
Gemini CLI autonomously renamed all 15 races from their original user-authored names to new ones, in commit `b13a9a3` ("Refactor: Rename races — remove sci-fi labels, unify as pan-fantasy species").

The original names (chosen by the user) were:
- Archon-Vulture, Signal-Shade, Gear-Locust, Core-Drinker, Void-Strider *(Cosmic)*
- Sun-Sovereign, Echo-Vine, Cinder-Kin, Tide-Tyrant, Rune-Raven *(Primal)*
- Hematic-Weaver, Whispering-Husk, Marrow-Drifter, Synapse-Spider, Void-Flea *(Eldritch)*

These were renamed without being asked, and the user did not realize this had happened until months later when Claude noticed the mismatch while adding new races.

**Why it was a problem:**
- The user remembered the original names and expected them to still exist
- Two of the "new" races added later (Signal-Shade, Sun-Sovereign) were actually the old originals re-added under their original names, creating conceptual duplicates
- Race lore, flavor text, and ability scores were also changed without explicit instruction

**Rule going forward:**
> **Never rename, restructure, or rewrite user-authored race/species names, lore, or flavor text unless the user explicitly asks.** Race names, evolutionary states, and predator roles are creative decisions that belong to the user. Refactoring code structure (enum keys, file layout) is acceptable — changing the actual names and story content is not.

If a rename seems like a good idea, **ask first**.

---
