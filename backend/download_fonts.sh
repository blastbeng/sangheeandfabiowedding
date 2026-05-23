#!/bin/sh
set +e   # do not exit on error

FONTS_DIR="/app/fonts"
mkdir -p "$FONTS_DIR"

# Great Vibes (cursive)
if [ ! -f "$FONTS_DIR/GreatVibes-Regular.ttf" ]; then
    echo "Downloading GreatVibes-Regular.ttf..."
    wget -q -O "$FONTS_DIR/GreatVibes-Regular.ttf" \
        "https://github.com/google/fonts/raw/main/ofl/greatvibes/GreatVibes-Regular.ttf" || \
        echo "WARNING: Failed to download GreatVibes-Regular.ttf"
fi

# Noto Sans KR (Korean)
if [ ! -f "$FONTS_DIR/NotoSansKR-Regular.ttf" ]; then
    echo "Downloading NotoSansKR-Regular.ttf..."
    wget -q -O "$FONTS_DIR/NotoSansKR-Regular.ttf" \
        "https://github.com/google/fonts/raw/main/ofl/notosanskr/NotoSansKR-Regular.ttf" || \
        echo "WARNING: Failed to download NotoSansKR-Regular.ttf"
fi

# Serif font (Crimson Text) – saved as Georgia.ttf to match existing code
if [ ! -f "$FONTS_DIR/Georgia.ttf" ]; then
    echo "Downloading Georgia.ttf (Crimson Text)..."
    wget -q -O "$FONTS_DIR/Georgia.ttf" \
        "https://github.com/google/fonts/raw/main/ofl/crimsontext/CrimsonText-Regular.ttf" || \
        echo "WARNING: Failed to download Georgia.ttf"
fi

echo "Font download script finished."
