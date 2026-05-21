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
CAP_ARCHIVE="/tmp/cap_model.tar.gz"
CAP_URL="https://www.kaggle.com/api/v1/models/google/mobilenet-v2/tensorFlow2/100-224-classification/2/download"

if [ -f "$CAP_MODEL" ] && [ -s "$CAP_MODEL" ] && [ "$(head -c 4 "$CAP_MODEL")" = "TFL3" ]; then
    echo "Caption classifier model already exists and is valid, skipping download."
else
    rm -f "$CAP_MODEL" "$CAP_ARCHIVE"
    echo "Downloading caption classifier model from Kaggle..."
    if curl -fSL --retry 5 --retry-delay 5 --connect-timeout 30 --max-time 120 \
         -o "$CAP_ARCHIVE" "$CAP_URL"; then
        echo "Extracting caption classifier model..."
        TFLITE_FILE=$(tar -tzf "$CAP_ARCHIVE" | grep '\.tflite$' | head -1)
        if [ -n "$TFLITE_FILE" ]; then
            tar -xzf "$CAP_ARCHIVE" -C /tmp "$TFLITE_FILE"
            mv "/tmp/$TFLITE_FILE" "$CAP_MODEL"
            rm -f "$CAP_ARCHIVE"
            if [ -s "$CAP_MODEL" ] && [ "$(head -c 4 "$CAP_MODEL")" = "TFL3" ]; then
                echo "Caption classifier model downloaded and extracted successfully."
            else
                echo "WARNING: Extracted caption_classifier.tflite is invalid – continuing without it."
                rm -f "$CAP_MODEL"
            fi
        else
            echo "WARNING: No .tflite file found in the Kaggle archive – continuing without caption classifier."
            rm -f "$CAP_ARCHIVE"
        fi
    else
        echo "WARNING: caption classifier download failed – continuing without it."
        rm -f "$CAP_ARCHIVE"
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
