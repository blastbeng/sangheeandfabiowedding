#!/bin/sh
if ! command -v curl >/dev/null 2>&1; then
    echo "ERROR: curl is required but not installed."
    exit 1
fi

MODELS_DIR="/app/models"
mkdir -p "$MODELS_DIR"

# --- similarity_model.tflite (feature vector) ---
SIM_MODEL="$MODELS_DIR/similarity_model.tflite"
SIM_URL="https://tfhub.dev/google/lite-model/mobilenet_v2/1.0_224/feature-vector/1?lite-format=tflite"

if [ -f "$SIM_MODEL" ] && [ -s "$SIM_MODEL" ] && [ "$(head -c 4 "$SIM_MODEL")" = "TFL3" ]; then
    echo "Similarity model already exists and is valid, skipping download."
else
    rm -f "$SIM_MODEL"
    echo "Downloading similarity model..."
    curl -fSL --compressed --retry 5 --retry-delay 5 --connect-timeout 30 --max-time 120 \
         -o "$SIM_MODEL" "$SIM_URL" || echo "WARNING: similarity model download failed"
    if [ -s "$SIM_MODEL" ] && [ "$(head -c 4 "$SIM_MODEL")" = "TFL3" ]; then
        echo "Similarity model downloaded successfully."
    else
        echo "WARNING: similarity_model.tflite is invalid or missing – continuing without it."
        rm -f "$SIM_MODEL"
    fi
fi

# --- caption_classifier.tflite (classification) ---
CAP_MODEL="$MODELS_DIR/caption_classifier.tflite"
CAP_URL="https://huggingface.co/qualcomm/MobileNet-v2/resolve/66db89e6808487c877f4e663a9f43d423b811f2f/MobileNet-v2.tflite"

if [ -f "$CAP_MODEL" ] && [ -s "$CAP_MODEL" ] && [ "$(head -c 4 "$CAP_MODEL")" = "TFL3" ]; then
    echo "Caption classifier model already exists and is valid, skipping download."
else
    rm -f "$CAP_MODEL"
    echo "Downloading caption classifier model..."
    curl -fSL --compressed --retry 5 --retry-delay 5 --connect-timeout 30 --max-time 120 \
         -o "$CAP_MODEL" "$CAP_URL" || echo "WARNING: caption classifier download failed"
    if [ -s "$CAP_MODEL" ] && [ "$(head -c 4 "$CAP_MODEL")" = "TFL3" ]; then
        echo "Caption classifier model downloaded successfully."
    else
        echo "WARNING: caption_classifier.tflite is invalid or missing – continuing without it."
        rm -f "$CAP_MODEL"
    fi
fi

# --- imagenet_labels.json ---
LABELS_FILE="$MODELS_DIR/imagenet_labels.json"
LABELS_URL="https://storage.googleapis.com/download.tensorflow.org/data/ImageNetLabels.txt"

if [ -f "$LABELS_FILE" ] && [ -s "$LABELS_FILE" ]; then
    echo "ImageNet labels already exist and are non-empty, skipping download."
else
    rm -f "$LABELS_FILE"
    echo "Downloading ImageNet labels..."
    curl -fSL --retry 5 --retry-delay 5 --connect-timeout 30 --max-time 60 \
         -o /tmp/ImageNetLabels.txt "$LABELS_URL"
    python3 -c "
import json
with open('/tmp/ImageNetLabels.txt') as f:
    labels = [line.strip() for line in f if line.strip()]
with open('$LABELS_FILE', 'w') as f:
    json.dump(labels, f)
"
    rm /tmp/ImageNetLabels.txt
    echo "ImageNet labels downloaded and converted."
fi

echo "All models ready."
