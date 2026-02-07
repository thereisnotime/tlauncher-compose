#!/bin/bash
# Install desktop launcher for Minecraft
#
# This script installs the .desktop file with correct paths

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_FILE="$HOME/.local/share/applications/minecraft-launcher.desktop"
ICON_DIR="$HOME/.local/share/icons"

echo "Installing Minecraft Launcher desktop integration..."

# Create directories if they don't exist
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$ICON_DIR"

# Copy icon
if [ -f "$SCRIPT_DIR/icon.png" ]; then
    cp "$SCRIPT_DIR/icon.png" "$ICON_DIR/minecraft-launcher.png"
    echo "✓ Icon installed to $ICON_DIR/minecraft-launcher.png"
else
    echo "⚠ Warning: icon.png not found. Generate it first with ImageMagick:"
    echo "  convert icon.svg -resize 256x256 icon.png"
fi

# Generate .desktop file with correct paths
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Minecraft Launcher
Comment=Launch Minecraft with TLauncher in a containerized environment
Exec=python3 $SCRIPT_DIR/minecraft.py
Path=$SCRIPT_DIR
Icon=minecraft-launcher
Terminal=false
Categories=Game;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"
echo "✓ Desktop file installed to $DESKTOP_FILE"

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications"
    echo "✓ Desktop database updated"
fi

echo ""
echo "✓ Installation complete!"
echo "  The Minecraft Launcher should now appear in your application menu."
echo ""
echo "To uninstall:"
echo "  rm $DESKTOP_FILE"
echo "  rm $ICON_DIR/minecraft-launcher.png"
