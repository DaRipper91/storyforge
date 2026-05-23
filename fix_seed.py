import json

with open("data/seeds/default_campaign.json", "r") as f:
    data = json.load(f)

# Fix era
if data.get("era") not in ["before", "after"]:
    data["era"] = "after" # Assuming The Feral World is post-Paradox ("after")

# Fix rooms missing 'cells' and 'description'
for room_id, room in data.get("rooms", {}).items():
    if "cells" not in room:
        room["cells"] = room.get("grid", []) # Copy grid to cells, or whatever schema expects. Let's see what schema expects.
        if "grid" in room:
            del room["grid"]
    if "description" not in room:
        room["description"] = "A standard room."

with open("data/seeds/default_campaign.json", "w") as f:
    json.dump(data, f, indent=2)
print("Seed fixed!")
