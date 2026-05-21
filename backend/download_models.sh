#!/bin/sh
set -e

MODELS_DIR="/app/models"
mkdir -p "$MODELS_DIR"

# --- similarity_model.tflite (feature vector) ---
SIM_MODEL="$MODELS_DIR/similarity_model.tflite"
SIM_URL="https://tfhub.dev/google/lite-model/mobilenet_v2/1.0_224/feature-vector/1?lite-format=tflite"

if [ ! -f "$SIM_MODEL" ]; then
    echo "Downloading similarity model..."
    wget -q --show-progress --retry-connrefused --waitretry=5 --timeout=120 \
         -O "$SIM_MODEL" "$SIM_URL"
    # Verify it's a valid TFLite file
    if [ "$(head -c 4 "$SIM_MODEL")" != "TFL3" ]; then
        echo "ERROR: similarity_model.tflite is not a valid TFLite file!"
        rm -f "$SIM_MODEL"
        exit 1
    fi
    echo "Similarity model downloaded successfully."
else
    echo "Similarity model already exists, skipping download."
fi

# --- caption_classifier.tflite (classification) ---
CAP_MODEL="$MODELS_DIR/caption_classifier.tflite"
CAP_URL="https://tfhub.dev/google/lite-model/mobilenet_v2/1.0_224/1?lite-format=tflite"

if [ ! -f "$CAP_MODEL" ]; then
    echo "Downloading caption classifier model..."
    wget -q --show-progress --retry-connrefused --waitretry=5 --timeout=120 \
         -O "$CAP_MODEL" "$CAP_URL"
    if [ "$(head -c 4 "$CAP_MODEL")" != "TFL3" ]; then
        echo "ERROR: caption_classifier.tflite is not a valid TFLite file!"
        rm -f "$CAP_MODEL"
        exit 1
    fi
    echo "Caption classifier model downloaded successfully."
else
    echo "Caption classifier model already exists, skipping download."
fi

# --- imagenet_labels.json ---
LABELS_FILE="$MODELS_DIR/imagenet_labels.json"
LABELS_URL="https://storage.googleapis.com/download.tensorflow.org/data/ImageNetLabels.txt"

if [ ! -f "$LABELS_FILE" ]; then
    echo "Downloading ImageNet labels..."
    wget -q --show-progress --retry-connrefused --waitretry=5 --timeout=60 \
         -O /tmp/ImageNetLabels.txt "$LABELS_URL"
    # Convert text file (one label per line) to JSON array
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
    echo "ImageNet labels already exist, skipping download."
fi

echo "All models ready."
