import io
import logging
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration, MarianMTModel, MarianTokenizer
import torch

logger = logging.getLogger(__name__)

# ---------- lazy model loading ----------
_caption_processor = None
_caption_model = None
_translator_it = None
_translator_ko = None
_tokenizer_it = None
_tokenizer_ko = None


def _load_caption_model():
    global _caption_processor, _caption_model
    if _caption_model is None:
        logger.info("Loading BLIP image captioning model...")
        _caption_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        _caption_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        if torch.cuda.is_available():
            _caption_model = _caption_model.to("cuda")
        _caption_model.eval()
    return _caption_processor, _caption_model


def _load_translator(lang):
    global _translator_it, _translator_ko, _tokenizer_it, _tokenizer_ko
    if lang == 'it':
        if _translator_it is None:
            logger.info("Loading English→Italian translation model...")
            _tokenizer_it = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-it")
            _translator_it = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-it")
            if torch.cuda.is_available():
                _translator_it = _translator_it.to("cuda")
            _translator_it.eval()
        return _tokenizer_it, _translator_it
    else:  # ko
        if _translator_ko is None:
            logger.info("Loading English→Korean translation model...")
            _tokenizer_ko = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-ko")
            _translator_ko = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-ko")
            if torch.cuda.is_available():
                _translator_ko = _translator_ko.to("cuda")
            _translator_ko.eval()
        return _tokenizer_ko, _translator_ko


def generate_english_caption(image_bytes: bytes) -> str:
    processor, model = _load_caption_model()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    inputs = processor(image, return_tensors="pt")
    if torch.cuda.is_available():
        inputs = {k: v.to("cuda") for k, v in inputs.items()}
    with torch.no_grad():
        out = model.generate(**inputs, max_length=50, num_beams=5)
    caption = processor.decode(out[0], skip_special_tokens=True)
    return caption.strip()


def translate_text(text: str, target_lang: str) -> str:
    tokenizer, model = _load_translator(target_lang)
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    if torch.cuda.is_available():
        inputs = {k: v.to("cuda") for k, v in inputs.items()}
    with torch.no_grad():
        translated = model.generate(**inputs)
    return tokenizer.decode(translated[0], skip_special_tokens=True).strip()
