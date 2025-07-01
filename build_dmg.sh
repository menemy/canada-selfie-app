#!/bin/bash
echo "🍁 Building Canada Selfie App DMG for macOS... 🍁"
echo

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Error: DMG creation is only supported on macOS"
    exit 1
fi

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Build the app first
echo "Building application bundle..."
pyinstaller -y canada_selfie.spec

if [ $? -ne 0 ]; then
    echo "Build failed!"
    exit 1
fi

# Create .app bundle structure for macOS
APP_NAME="Canada Selfie"
APP_BUNDLE="dist/${APP_NAME}.app"
DMG_NAME="Canada-Selfie-App"

echo "Creating macOS app bundle..."

# Remove existing bundle
rm -rf "$APP_BUNDLE"

# Create .app structure
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# Copy executable to MacOS folder
cp dist/CanadaSelfieApp "$APP_BUNDLE/Contents/MacOS/"

# Create Info.plist
cat > "$APP_BUNDLE/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>CanadaSelfieApp</string>
    <key>CFBundleIdentifier</key>
    <string>com.canadaselfie.app</string>
    <key>CFBundleName</key>
    <string>Canada Selfie</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSCameraUsageDescription</key>
    <string>Canada Selfie needs camera access to take awesome Canadian-themed selfies!</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.photography</string>
</dict>
</plist>
EOF

# Copy icon if available
if [ -f "emoji_icons/maple_leaf.png" ]; then
    echo "Adding app icon..."
    # Convert PNG to ICNS (requires iconutil on macOS)
    mkdir -p "icon.iconset"
    
    # Create different sizes for the icon
    sips -z 16 16 "emoji_icons/maple_leaf.png" --out "icon.iconset/icon_16x16.png" 2>/dev/null
    sips -z 32 32 "emoji_icons/maple_leaf.png" --out "icon.iconset/icon_16x16@2x.png" 2>/dev/null
    sips -z 32 32 "emoji_icons/maple_leaf.png" --out "icon.iconset/icon_32x32.png" 2>/dev/null
    sips -z 64 64 "emoji_icons/maple_leaf.png" --out "icon.iconset/icon_32x32@2x.png" 2>/dev/null
    sips -z 128 128 "emoji_icons/maple_leaf.png" --out "icon.iconset/icon_128x128.png" 2>/dev/null
    sips -z 256 256 "emoji_icons/maple_leaf.png" --out "icon.iconset/icon_128x128@2x.png" 2>/dev/null
    sips -z 256 256 "emoji_icons/maple_leaf.png" --out "icon.iconset/icon_256x256.png" 2>/dev/null
    sips -z 512 512 "emoji_icons/maple_leaf.png" --out "icon.iconset/icon_256x256@2x.png" 2>/dev/null
    sips -z 512 512 "emoji_icons/maple_leaf.png" --out "icon.iconset/icon_512x512.png" 2>/dev/null
    
    # Create ICNS file
    iconutil -c icns "icon.iconset" -o "$APP_BUNDLE/Contents/Resources/icon.icns" 2>/dev/null
    
    # Clean up
    rm -rf "icon.iconset"
    
    # Update Info.plist with icon
    /usr/libexec/PlistBuddy -c "Add :CFBundleIconFile string icon" "$APP_BUNDLE/Contents/Info.plist" 2>/dev/null
fi

# Make executable
chmod +x "$APP_BUNDLE/Contents/MacOS/CanadaSelfieApp"

echo "Creating DMG..."

# Create temporary DMG directory
DMG_DIR="dmg_temp"
rm -rf "$DMG_DIR"
mkdir "$DMG_DIR"

# Copy app bundle to DMG directory
cp -R "$APP_BUNDLE" "$DMG_DIR/"

# Create Applications symlink
ln -s /Applications "$DMG_DIR/Applications"

# Don't copy README to DMG - keep it clean

# Create DMG
hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_DIR" -ov -format UDZO "${DMG_NAME}.dmg"

if [ $? -eq 0 ]; then
    echo
    echo "✅ DMG created successfully!"
    echo "File: ${DMG_NAME}.dmg"
    echo "Size: $(du -h "${DMG_NAME}.dmg" | cut -f1)"
    echo
    echo "You can now distribute this DMG file to macOS users."
    echo "They can simply drag the app to Applications folder to install."
else
    echo "❌ DMG creation failed!"
    exit 1
fi

# Clean up
rm -rf "$DMG_DIR"

echo "Done! 🍁"