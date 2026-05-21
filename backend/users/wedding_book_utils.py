import io
import logging
from PIL import Image
import cv2
import numpy as np
from .cloud_clients import get_file_from_cloud
from .models import Media

logger = logging.getLogger(__name__)

ROMANTIC_ADJECTIVES = [
    "romantic", "joyful", "tender", "magical", "elegant", "sweet",
    "radiant", "intimate", "blissful", "enchanting", "graceful",
    "heartwarming", "dreamy", "passionate", "serene"
]


def _pick_adjective(caption: str) -> str:
    """Pick a romantic adjective based on keywords in the caption."""
    caption_lower = caption.lower()
    if any(w in caption_lower for w in ["dance", "dancing", "party"]):
        return "joyful"
    if any(w in caption_lower for w in ["kiss", "kissing", "embrace"]):
        return "passionate"
    if any(w in caption_lower for w in ["smile", "laugh", "happy"]):
        return "radiant"
    if any(w in caption_lower for w in ["sunset", "golden", "light"]):
        return "magical"
    if any(w in caption_lower for w in ["flower", "bouquet", "garden"]):
        return "enchanting"
    if any(w in caption_lower for w in ["ceremony", "vows", "ring"]):
        return "elegant"
    # fallback: random from list
    import random
    return random.choice(ROMANTIC_ADJECTIVES)


# ---------- lazy model loading ----------
_caption_feature_extractor = None
_caption_tokenizer = None
_caption_model = None
_translator_it = None
_translator_ko = None
_tokenizer_it = None
_tokenizer_ko = None


def _load_caption_model():
    global _caption_feature_extractor, _caption_tokenizer, _caption_model
    if _caption_model is None:
        from transformers import VisionEncoderDecoderModel, ViTFeatureExtractor, AutoTokenizer
        import torch
        logger.info("Loading ViT-GPT2 image captioning model (optimized for CPU)...")
        _caption_feature_extractor = ViTFeatureExtractor.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
        _caption_tokenizer = AutoTokenizer.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
        _caption_model = VisionEncoderDecoderModel.from_pretrained(
            "nlpconnect/vit-gpt2-image-captioning",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        )
        # Limit CPU threads to avoid overloading the Raspberry Pi
        torch.set_num_threads(2)
        if torch.cuda.is_available():
            _caption_model = _caption_model.to("cuda")
        else:
            _caption_model = _caption_model.to('cpu')
        _caption_model.eval()
    return _caption_feature_extractor, _caption_tokenizer, _caption_model


def _load_translator(lang):
    global _translator_it, _translator_ko, _tokenizer_it, _tokenizer_ko
    if lang == 'it':
        if _translator_it is None:
            from transformers import MarianMTModel, MarianTokenizer
            import torch
            logger.info("Loading English→Italian translation model (optimized)...")
            _tokenizer_it = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-it")
            _translator_it = MarianMTModel.from_pretrained(
                "Helsinki-NLP/opus-mt-en-it",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            torch.set_num_threads(2)
            if torch.cuda.is_available():
                _translator_it = _translator_it.to("cuda")
            else:
                _translator_it = _translator_it.to('cpu')
            _translator_it.eval()
        return _tokenizer_it, _translator_it
    else:  # ko
        if _translator_ko is None:
            from transformers import MarianMTModel, MarianTokenizer
            import torch
            logger.info("Loading English→Korean translation model (optimized)...")
            _tokenizer_ko = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-ko")
            _translator_ko = MarianMTModel.from_pretrained(
                "Helsinki-NLP/opus-mt-en-ko",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            torch.set_num_threads(2)
            if torch.cuda.is_available():
                _translator_ko = _translator_ko.to("cuda")
            else:
                _translator_ko = _translator_ko.to('cpu')
            _translator_ko.eval()
        return _tokenizer_ko, _translator_ko


def generate_english_caption(image_bytes: bytes) -> str:
    import torch
    feature_extractor, tokenizer, model = _load_caption_model()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    pixel_values = feature_extractor(images=image, return_tensors="pt").pixel_values
    if torch.cuda.is_available():
        pixel_values = pixel_values.to("cuda")
    with torch.no_grad():
        out = model.generate(pixel_values, max_length=50, num_beams=5)
    raw_caption = tokenizer.decode(out[0], skip_special_tokens=True).strip()

    # Make it wedding-themed
    adjective = _pick_adjective(raw_caption)
    # Capitalize first letter of raw caption
    if raw_caption:
        raw_caption = raw_caption[0].upper() + raw_caption[1:]
    creative_caption = f"A {adjective} moment: {raw_caption}"
    return creative_caption


def translate_text(text: str, target_lang: str) -> str:
    import torch
    tokenizer, model = _load_translator(target_lang)
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    if torch.cuda.is_available():
        inputs = {k: v.to("cuda") for k, v in inputs.items()}
    with torch.no_grad():
        translated = model.generate(**inputs)
    return tokenizer.decode(translated[0], skip_special_tokens=True).strip()


def unload_models():
    """Unload all AI models to free memory on Raspberry Pi."""
    import torch
    global _caption_feature_extractor, _caption_tokenizer, _caption_model
    global _translator_it, _translator_ko, _tokenizer_it, _tokenizer_ko
    _caption_feature_extractor = None
    _caption_tokenizer = None
    _caption_model = None
    _translator_it = None
    _translator_ko = None
    _tokenizer_it = None
    _tokenizer_ko = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _compute_image_score(media_obj):
    """
    Compute a simple quality score for a media item.
    Higher is better. Uses:
      - face bonus (1 if face tags exist)
      - sharpness (Laplacian variance, normalized)
      - resolution (normalized by 12 MP)
    All processing is done on a downscaled image to stay fast on RPi5.
    """
    score = 0.0
    # Face bonus
    if media_obj.face_tags.exists():
        score += 1.0

    # Image sharpness and resolution
    try:
        content, _ = get_file_from_cloud(media_obj)
        if content is None:
            # fallback to local file
            if media_obj.file and media_obj.file.storage.exists(media_obj.file.name):
                with media_obj.file.open('rb') as f:
                    content = f.read()
        if content:
            pil_img = Image.open(io.BytesIO(content)).convert('RGB')
            w, h = pil_img.size
            # Resolution score (cap at 12 MP)
            mp = (w * h) / 1_000_000
            resolution_score = min(mp / 12.0, 1.0)
            score += resolution_score

            # Sharpness: resize to max 300px, convert to grayscale, compute Laplacian variance
            pil_img.thumbnail((300, 300), Image.LANCZOS)
            gray = np.array(pil_img.convert('L'))
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            # Normalize: typical values range 0-500, cap at 500
            sharpness_score = min(laplacian_var / 500.0, 1.0)
            score += sharpness_score
    except Exception as e:
        logger.warning(f"Could not compute score for media {media_obj.id}: {e}")

    return score


def auto_select_media(already_selected_ids, target=20):
    """
    Given a list of already selected media IDs, return a list of exactly `target`
    media IDs by adding the best remaining approved media (based on quality score).
    """
    already_set = set(already_selected_ids)
    # Fetch all approved media not already selected
    candidates = Media.objects.filter(status='approved', media_type='image').exclude(id__in=already_set)
    # Compute scores
    scored = []
    for media in candidates:
        s = _compute_image_score(media)
        scored.append((media.id, s))
    # Sort descending by score
    scored.sort(key=lambda x: x[1], reverse=True)
    # Take as many as needed to reach target
    needed = target - len(already_selected_ids)
    additional_ids = [mid for mid, _ in scored[:needed]]
    return list(already_selected_ids) + additional_ids
