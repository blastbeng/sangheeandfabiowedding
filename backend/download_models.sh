#!/bin/sh
# -------------------------------------------------------------------
# Download helper models for the wedding app.
# All failures are non‑fatal – the container will start even if a
# model is missing.
# -------------------------------------------------------------------

MODELS_DIR="/app/models"
mkdir -p "$MODELS_DIR"

# -------------------------------------------------------------------
# 1. MobileNetV2 model (used for both similarity and caption tasks)
# -------------------------------------------------------------------
MODEL_URL="https://huggingface.co/qualcomm/MobileNet-v2/resolve/66db89e6808487c877f4e663a9f43d423b811f2f/MobileNet-v2.tflite"
SIM_MODEL="$MODELS_DIR/similarity_model.tflite"
CAP_MODEL="$MODELS_DIR/caption_classifier.tflite"

# Check if both files already exist and are valid
SIM_OK=0
CAP_OK=0
[ -s "$SIM_MODEL" ] && [ "$(head -c 4 "$SIM_MODEL")" = "TFL3" ] && SIM_OK=1
[ -s "$CAP_MODEL" ] && [ "$(head -c 4 "$CAP_MODEL")" = "TFL3" ] && CAP_OK=1

if [ "$SIM_OK" -eq 1 ] && [ "$CAP_OK" -eq 1 ]; then
    echo "MobileNetV2 model already exists and is valid, skipping download."
else
    echo "Downloading MobileNetV2 model..."
    TMP_MODEL="/tmp/mobilenet_v2.tflite"
    rm -f "$TMP_MODEL"

    if wget -q --show-progress --tries=5 --timeout=30 \
         --header="Accept-Encoding: identity" \
         -O "$TMP_MODEL" "$MODEL_URL"; then
        if [ -s "$TMP_MODEL" ] && [ "$(head -c 4 "$TMP_MODEL")" = "TFL3" ]; then
            # Copy to both destinations
            cp "$TMP_MODEL" "$SIM_MODEL"
            cp "$TMP_MODEL" "$CAP_MODEL"
            rm -f "$TMP_MODEL"
            echo "MobileNetV2 model downloaded and copied successfully."
        else
            echo "WARNING: Downloaded file is invalid or empty – continuing without model."
            rm -f "$TMP_MODEL"
        fi
    else
        echo "WARNING: MobileNetV2 model download failed – continuing without it."
        rm -f "$TMP_MODEL"
    fi
fi

# -------------------------------------------------------------------
# 2. ImageNet labels
# -------------------------------------------------------------------
LABELS_FILE="$MODELS_DIR/imagenet_labels.json"
LABELS_URL="https://storage.googleapis.com/download.tensorflow.org/data/ImageNetLabels.txt"

if [ -f "$LABELS_FILE" ] && [ -s "$LABELS_FILE" ]; then
    echo "ImageNet labels already exist and are non-empty, skipping download."
else
    rm -f "$LABELS_FILE"
    echo "Downloading ImageNet labels..."
    if curl -fSL --retry 5 --retry-delay 5 --connect-timeout 30 --max-time 60 \
         -o /tmp/ImageNetLabels.txt "$LABELS_URL"; then
        python3 -c "
import json
with open('/tmp/ImageNetLabels.txt') as f:
    labels = [line.strip() for line in f if line.strip()]
with open('$LABELS_FILE', 'w') as f:
    json.dump(labels, f)
"
        rm /tmp/ImageNetLabels.txt
        echo "ImageNet labels downloaded and converted."
    else
        echo "WARNING: ImageNet labels download failed – continuing without them."
    fi
fi

echo "All models ready."
