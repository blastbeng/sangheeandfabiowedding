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
TFLITE_URL="https://huggingface.co/qualcomm/MobileNet-v2/resolve/66db89e6808487c877f4e663a9f43d423b811f2f/MobileNet-v2.tflite"

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

# -------------------------------------------------------------------
# Translation models (English → Italian, English → Korean)
# Used by the wedding book caption generation.
# -------------------------------------------------------------------
echo "Checking translation models..."
python3 -c "
import os, sys
from pathlib import Path

# Hugging Face cache location (respects HF_HOME, defaults to ~/.cache/huggingface)
cache_home = Path(os.environ.get('HF_HOME', Path.home() / '.cache' / 'huggingface'))
hub_dir = cache_home / 'hub'

models = [
    'Helsinki-NLP/opus-mt-tc-big-en-it',
    'Helsinki-NLP/opus-mt-tc-big-en-ko',
]

all_cached = True
for model_id in models:
    # Transformers stores models under models--org--model
    dir_name = 'models--' + model_id.replace('/', '--')
    model_dir = hub_dir / dir_name
    # A valid cache contains a 'snapshots' directory with at least one snapshot
    if model_dir.is_dir() and (model_dir / 'snapshots').is_dir() and any((model_dir / 'snapshots').iterdir()):
        print(f'{model_id} already cached, skipping.')
    else:
        all_cached = False
        print(f'{model_id} not cached, will download.')

if all_cached:
    print('All translation models are cached.')
    sys.exit(0)
else:
    print('Downloading missing translation models...')
    from transformers import MarianTokenizer, MarianMTModel
    for model_id in models:
        print(f'Downloading {model_id}...')
        MarianTokenizer.from_pretrained(model_id)
        MarianMTModel.from_pretrained(model_id)
    print('Translation models downloaded successfully.')
"

echo "All models ready."
