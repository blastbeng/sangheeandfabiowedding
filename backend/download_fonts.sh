#!/bin/sh
set +e   # do not exit on error

FONTS_DIR="/app/fonts"
mkdir -p "$FONTS_DIR"

# ---------- Elegant (default) ----------
if [ ! -f "$FONTS_DIR/GreatVibes-Regular.ttf" ]; then
    echo "Downloading GreatVibes-Regular.ttf..."
    wget -q -O "$FONTS_DIR/GreatVibes-Regular.ttf" \
        "https://github.com/google/fonts/raw/main/ofl/greatvibes/GreatVibes-Regular.ttf" || \
        echo "WARNING: Failed to download GreatVibes-Regular.ttf"
fi

if [ ! -f "$FONTS_DIR/CrimsonText-Regular.ttf" ]; then
    echo "Downloading CrimsonText-Regular.ttf..."
    wget -q -O "$FONTS_DIR/CrimsonText-Regular.ttf" \
        "https://github.com/google/fonts/raw/main/ofl/crimsontext/CrimsonText-Regular.ttf" || \
        echo "WARNING: Failed to download CrimsonText-Regular.ttf"
fi

# ---------- Classic ----------
if [ ! -f "$FONTS_DIR/Tangerine-Regular.ttf" ]; then
    echo "Downloading Tangerine-Regular.ttf..."
    wget -q -O "$FONTS_DIR/Tangerine-Regular.ttf" \
        "https://github.com/google/fonts/raw/main/ofl/tangerine/Tangerine-Regular.ttf" || \
        echo "WARNING: Failed to download Tangerine-Regular.ttf"
fi

if [ ! -f "$FONTS_DIR/PlayfairDisplay-Regular.ttf" ]; then
    echo "Downloading PlayfairDisplay-Regular.ttf..."
    wget -q -O "$FONTS_DIR/PlayfairDisplay-Regular.ttf" \
        "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay-Regular.ttf" || \
        echo "WARNING: Failed to download PlayfairDisplay-Regular.ttf"
fi

# ---------- Modern ----------
if [ ! -f "$FONTS_DIR/Montserrat-Regular.ttf" ]; then
    echo "Downloading Montserrat-Regular.ttf..."
    wget -q -O "$FONTS_DIR/Montserrat-Regular.ttf" \
        "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Regular.ttf" || \
        echo "WARNING: Failed to download Montserrat-Regular.ttf"
fi

if [ ! -f "$FONTS_DIR/Raleway-Regular.ttf" ]; then
    echo "Downloading Raleway-Regular.ttf..."
    wget -q -O "$FONTS_DIR/Raleway-Regular.ttf" \
        "https://github.com/google/fonts/raw/main/ofl/raleway/Raleway-Regular.ttf" || \
        echo "WARNING: Failed to download Raleway-Regular.ttf"
fi

# ---------- Vintage ----------
if [ ! -f "$FONTS_DIR/Pacifico-Regular.ttf" ]; then
    echo "Downloading Pacifico-Regular.ttf..."
    wget -q -O "$FONTS_DIR/Pacifico-Regular.ttf" \
        "https://github.com/google/fonts/raw/main/ofl/pacifico/Pacifico-Regular.ttf" || \
        echo "WARNING: Failed to download Pacifico-Regular.ttf"
fi

if [ ! -f "$FONTS_DIR/OldStandardTT-Regular.ttf" ]; then
    echo "Downloading OldStandardTT-Regular.ttf..."
    wget -q -O "$FONTS_DIR/OldStandardTT-Regular.ttf" \
        "https://github.com/google/fonts/raw/main/ofl/oldstandardtt/OldStandardTT-Regular.ttf" || \
        echo "WARNING: Failed to download OldStandardTT-Regular.ttf"
fi

# ---------- Romantic ----------
if [ ! -f "$FONTS_DIR/DancingScript-Regular.ttf" ]; then
    echo "Downloading DancingScript-Regular.ttf..."
    wget -q -O "$FONTS_DIR/DancingScript-Regular.ttf" \
        "https://github.com/google/fonts/raw/main/ofl/dancingscript/DancingScript-Regular.ttf" || \
        echo "WARNING: Failed to download DancingScript-Regular.ttf"
fi

if [ ! -f "$FONTS_DIR/Lora-Regular.ttf" ]; then
    echo "Downloading Lora-Regular.ttf..."
    wget -q -O "$FONTS_DIR/Lora-Regular.ttf" \
        "https://github.com/google/fonts/raw/main/ofl/lora/Lora-Regular.ttf" || \
        echo "WARNING: Failed to download Lora-Regular.ttf"
fi

# Korean font (used by all themes)
if [ ! -f "$FONTS_DIR/NotoSansKR-Regular.ttf" ]; then
    echo "Downloading NotoSansKR-Regular.ttf..."
    wget -q -O "$FONTS_DIR/NotoSansKR-Regular.ttf" \
        "https://github.com/google/fonts/raw/main/ofl/notosanskr/NotoSansKR-Regular.ttf" || \
        echo "WARNING: Failed to download NotoSansKR-Regular.ttf"
fi

echo "Font download script finished."
