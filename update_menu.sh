#!/bin/bash

# Get the absolute path to the directory containing this script
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GODOT_PROJECT="$PROJECT_ROOT/godot/project.godot"
ICON_PATH="$PROJECT_ROOT/godot/icon.svg"

DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/storyforge.desktop"

# Create the applications directory if it doesn't exist
mkdir -p "$DESKTOP_DIR"

# Write the .desktop file
cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Name=StoryForge
Comment=A Feral World Adventure
Exec=godot "$PROJECT_ROOT/godot/scenes/Boot.tscn"
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Game;RolePlaying;
EOF

chmod +x "$DESKTOP_FILE"

# Update the desktop database to refresh the menu
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$DESKTOP_DIR"
fi

echo "Successfully updated the application menu!"
echo "StoryForge can now be found in your 'Games' section."
