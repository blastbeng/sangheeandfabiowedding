#!/bin/sh
# -------------------------------------------------------------------
# Download helper models for the wedding app.
# All failures are non‑fatal – the container will start even if a
# model is missing.
# -------------------------------------------------------------------

MODELS_DIR="/app/models"
mkdir -p "$MODELS_DIR"

# -------------------------------------------------------------------
# ImageNet labels
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

# -------------------------------------------------------------------
# MobileNetV2 TFLite model (used for image classification, similarity
# ordering, and wedding-book clustering)
# -------------------------------------------------------------------
TFLITE_FILE="$MODELS_DIR/MobileNet-v2.tflite"
TFLITE_URL="https://storage.googleapis.com/download.tensorflow.org/models/tflite_11_05_08/mobilenet_v2_1.0_224.tflite"

if [ -f "$TFLITE_FILE" ] && [ -s "$TFLITE_FILE" ]; then
    echo "MobileNetV2 TFLite model already exists and is non-empty, skipping download."
else
    rm -f "$TFLITE_FILE"
    echo "Downloading MobileNetV2 TFLite model..."
    if curl -fSL --retry 5 --retry-delay 5 --connect-timeout 30 --max-time 300 \
         -o "$TFLITE_FILE" "$TFLITE_URL"; then
        echo "MobileNetV2 TFLite model downloaded successfully."
    else
        rm -f "$TFLITE_FILE"
        echo "WARNING: MobileNetV2 TFLite model download failed – continuing without it."
    fi
fi

echo "All models ready."
