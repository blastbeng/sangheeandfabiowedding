#!/bin/sh
set -e

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
    # Remove any existing invalid file
    rm -f "$SIM_MODEL"
    echo "Downloading similarity model..."
    curl -fSL --compressed --retry 5 --retry-delay 5 --connect-timeout 30 --max-time 120 \
         -o "$SIM_MODEL" "$SIM_URL"
    if [ ! -s "$SIM_MODEL" ]; then
        echo "ERROR: similarity_model.tflite is empty – download failed."
        rm -f "$SIM_MODEL"
        exit 1
    fi
    if [ "$(head -c 4 "$SIM_MODEL")" != "TFL3" ]; then
        echo "ERROR: similarity_model.tflite is not a valid TFLite file!"
        rm -f "$SIM_MODEL"
        exit 1
    fi
    echo "Similarity model downloaded successfully."
fi

# --- caption_classifier.tflite (classification) ---
CAP_MODEL="$MODELS_DIR/caption_classifier.tflite"
CAP_URL="https://tfhub.dev/google/lite-model/mobilenet_v2/1.0_224/1?lite-format=tflite"

if [ -f "$CAP_MODEL" ] && [ -s "$CAP_MODEL" ] && [ "$(head -c 4 "$CAP_MODEL")" = "TFL3" ]; then
    echo "Caption classifier model already exists and is valid, skipping download."
else
    rm -f "$CAP_MODEL"
    echo "Downloading caption classifier model..."
    curl -fSL --compressed --retry 5 --retry-delay 5 --connect-timeout 30 --max-time 120 \
         -o "$CAP_MODEL" "$CAP_URL"
    if [ ! -s "$CAP_MODEL" ]; then
        echo "ERROR: caption_classifier.tflite is empty – download failed."
        rm -f "$CAP_MODEL"
        exit 1
    fi
    if [ "$(head -c 4 "$CAP_MODEL")" != "TFL3" ]; then
        echo "ERROR: caption_classifier.tflite is not a valid TFLite file!"
        rm -f "$CAP_MODEL"
        exit 1
    fi
    echo "Caption classifier model downloaded successfully."
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
