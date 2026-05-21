import io
import logging
from PIL import Image
from transformers import VisionEncoderDecoderModel, ViTFeatureExtractor, AutoTokenizer, MarianMTModel, MarianTokenizer
import torch

logger = logging.getLogger(__name__)

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
    feature_extractor, tokenizer, model = _load_caption_model()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    pixel_values = feature_extractor(images=image, return_tensors="pt").pixel_values
    if torch.cuda.is_available():
        pixel_values = pixel_values.to("cuda")
    with torch.no_grad():
        out = model.generate(pixel_values, max_length=50, num_beams=5)
    caption = tokenizer.decode(out[0], skip_special_tokens=True)
    return caption.strip()


def translate_text(text: str, target_lang: str) -> str:
    tokenizer, model = _load_translator(target_lang)
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    if torch.cuda.is_available():
        inputs = {k: v.to("cuda") for k, v in inputs.items()}
    with torch.no_grad():
        translated = model.generate(**inputs)
    return tokenizer.decode(translated[0], skip_special_tokens=True).strip()


def unload_models():
    """Unload all AI models to free memory on Raspberry Pi."""
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
