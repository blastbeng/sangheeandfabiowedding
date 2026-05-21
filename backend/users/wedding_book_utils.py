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


# ---------- RPi5-optimized captioning ----------
_caption_classifier_interpreter = None
_caption_classifier_labels = None

def _load_caption_classifier():
    """Load the MobileNetV2 classification TFLite model and ImageNet labels."""
    global _caption_classifier_interpreter, _caption_classifier_labels
    if _caption_classifier_interpreter is not None:
        return _caption_classifier_interpreter, _caption_classifier_labels

    import tflite_runtime.interpreter as tflite
    import os, requests, json
    from django.conf import settings as django_settings

    MODEL_URL = (
        "https://storage.googleapis.com/download.tensorflow.org/"
        "models/tflite/model_zoo/vision_models/"
        "mobilenet_v2_1.0_224_quantized_1_default_1.tflite"
    )
    MODELS_DIR = os.path.join(django_settings.BASE_DIR, 'models')
    os.makedirs(MODELS_DIR, exist_ok=True)
    MODEL_PATH = os.path.join(MODELS_DIR, 'caption_classifier.tflite')
    LABELS_PATH = os.path.join(MODELS_DIR, 'imagenet_labels.json')

    if not os.path.exists(MODEL_PATH):
        logger.info("[caption] Downloading MobileNetV2 classification TFLite model...")
        resp = requests.get(MODEL_URL, timeout=120)
        resp.raise_for_status()
        content = resp.content
        # Validate TFLite magic bytes
        if not content.startswith(b'TFL3'):
            raise ValueError(
                f"Downloaded caption classifier model is not a valid TFLite file "
                f"(starts with {content[:4]!r}). URL may be invalid or returned an error page."
            )
        with open(MODEL_PATH, "wb") as f:
            f.write(content)

    if not os.path.exists(LABELS_PATH):
        # Download ImageNet class labels (simple list)
        LABELS_URL = "https://storage.googleapis.com/download.tensorflow.org/data/ImageNetLabels.txt"
        resp = requests.get(LABELS_URL, timeout=30)
        resp.raise_for_status()
        labels = [line.strip() for line in resp.text.splitlines()]
        with open(LABELS_PATH, "w") as f:
            json.dump(labels, f)

    with open(LABELS_PATH, "r") as f:
        _caption_classifier_labels = json.load(f)

    # Validate existing file before loading
    with open(MODEL_PATH, "rb") as f:
        header = f.read(4)
    if header != b'TFL3':
        os.remove(MODEL_PATH)
        raise ValueError(
            f"Cached caption classifier model is corrupt (header {header!r}). "
            f"Deleted {MODEL_PATH}. Please retry."
        )
    _caption_classifier_interpreter = tflite.Interpreter(model_path=MODEL_PATH)
    _caption_classifier_interpreter.allocate_tensors()
    return _caption_classifier_interpreter, _caption_classifier_labels


# Mapping of ImageNet class names (lowercase) to wedding-themed captions
CAPTION_TEMPLATES = {
    "bridegroom": "The groom, looking handsome and full of love.",
    "bride": "The beautiful bride, radiant with happiness.",
    "wedding": "A magical wedding moment to cherish forever.",
    "bouquet": "A stunning bouquet, symbol of love and new beginnings.",
    "cake": "The wedding cake, sweet and elegant.",
    "church": "A sacred ceremony in a beautiful church.",
    "altar": "At the altar, where two hearts become one.",
    "ring": "The exchange of rings, a promise of eternal love.",
    "dance": "A joyful dance, celebrating love and togetherness.",
    "kiss": "A tender kiss, sealing their vows.",
    "flower": "Delicate flowers, adding romance to the day.",
    "garden": "A romantic garden setting, full of natural beauty.",
    "table": "The reception table, elegantly set for the celebration.",
    "champagne": "A toast to love, laughter, and happily ever after.",
    "sunset": "A breathtaking sunset, painting the sky with love.",
    "couple": "The happy couple, lost in each other's eyes.",
    "dress": "The wedding dress, a vision of grace and beauty.",
    "suit": "Dressed to impress, ready for the big day.",
    "car": "The wedding car, ready to whisk them away.",
    "beach": "A dreamy beach wedding, with waves of love.",
    "mountain": "Love as high as the mountains, as deep as the valleys.",
    "tree": "Under the shade of love, a moment of peace.",
    "food": "Delicious food, shared with loved ones.",
    "music": "Music fills the air, hearts beat as one.",
    "confetti": "Confetti and joy, celebrating the newlyweds.",
    "hands": "Hand in hand, heart to heart.",
    "smile": "Smiles that light up the entire celebration.",
    "group": "Surrounded by family and friends, love multiplies.",
    "portrait": "A portrait of love, timeless and true.",
    "candle": "Candlelight romance, warm and intimate.",
    "wine": "Fine wine and fine company, a perfect pairing.",
    "decoration": "Beautiful decorations, setting the mood for love.",
    "invitation": "The invitation that started it all.",
    "shoe": "Every step a memory, every shoe a story.",
    "jewelry": "Sparkling jewelry, reflecting the joy within.",
    "makeup": "Getting ready, a moment of anticipation.",
    "mirror": "A reflection of happiness and excitement.",
    "window": "Looking out at a future full of love.",
    "door": "Opening the door to a new chapter together.",
    "path": "Walking the path of love, side by side.",
    "sky": "Under an endless sky, love knows no bounds.",
    "water": "Love flows like water, pure and eternal.",
    "fire": "The warmth of love, burning bright.",
    "light": "Bathed in light, a moment of pure bliss.",
    "shadow": "Even in shadows, love shines through.",
    "vintage": "A vintage touch, timeless romance.",
    "rustic": "Rustic charm, love in its purest form.",
    "elegant": "Elegance and grace, a day to remember.",
    "romantic": "Pure romance, captured forever.",
    "celebration": "A celebration of love, joy, and togetherness.",
    "party": "Let the party begin! Love is in the air.",
    "family": "Family, the foundation of love and support.",
    "friend": "Friends who become family, sharing the joy.",
    "child": "Little ones, adding innocence and delight.",
    "pet": "Furry friends, part of the love story.",
    "nature": "Nature's beauty, a perfect backdrop for love.",
    "city": "City lights, urban romance.",
    "country": "Country charm, love in the countryside.",
    "village": "A quaint village, a fairy-tale wedding.",
    "castle": "A castle wedding, fit for a king and queen.",
    "palace": "Royal love, majestic and grand.",
    "tent": "A tented celebration, cozy and intimate.",
    "balloon": "Balloons of joy, lifting spirits high.",
    "gift": "Gifts of love, wrapped with care.",
    "letter": "Love letters, words from the heart.",
    "book": "A new chapter begins, written in love.",
    "clock": "Time stands still when love is true.",
    "heart": "Hearts full of love, beating as one.",
    "star": "Starry-eyed and full of wonder.",
    "moon": "Under the moonlight, love glows.",
    "sun": "Sunshine and smiles, a perfect day.",
    "rain": "Rain on your wedding day? Good luck and romance!",
    "snow": "A winter wonderland wedding, pure and magical.",
    "autumn": "Autumn leaves, a tapestry of love.",
    "spring": "Spring blossoms, new beginnings.",
    "summer": "Summer love, warm and bright.",
    "winter": "Winter romance, cozy and warm.",
    "holiday": "Holiday cheer, love all around.",
    "travel": "A journey of love, adventure awaits.",
    "map": "Mapping out a lifetime of happiness.",
    "compass": "Love guides the way.",
    "anchor": "Anchored in love, steady and strong.",
    "boat": "Sailing into forever.",
    "airplane": "Love takes flight.",
    "train": "On the right track to happily ever after.",
    "bicycle": "Pedaling through life together.",
    "motorcycle": "Riding into the sunset, wild and free.",
    "horse": "A fairytale carriage, love in motion.",
    "dog": "Man's best friend, part of the family.",
    "cat": "Purrfect love, cozy and content.",
    "bird": "Love birds, singing a sweet melody.",
    "butterfly": "Butterflies of excitement, love is in the air.",
    "rose": "A single rose, a thousand words of love.",
    "lily": "Pure as a lily, love blossoms.",
    "tulip": "Tulips of passion, declaring love.",
    "daisy": "Innocence and joy, a daisy chain of love.",
    "sunflower": "Sunflowers turn to the sun, like hearts to love.",
    "lavender": "Lavender fields, calming and romantic.",
    "peony": "Peonies of prosperity, a flourishing love.",
    "orchid": "Exotic beauty, rare and precious love.",
    "cherry blossom": "Cherry blossoms, fleeting and beautiful like moments.",
    "wreath": "A wreath of welcome, love encircles all.",
    "garland": "Garlands of joy, adorning the celebration.",
    "ribbon": "Ribbons of love, tying the knot.",
    "lace": "Delicate lace, intricate and beautiful.",
    "pearl": "Pearls of wisdom, a love that grows.",
    "crystal": "Crystal clear love, transparent and true.",
    "gold": "Golden moments, treasured forever.",
    "silver": "Silver linings, love shines through.",
    "diamond": "Diamonds are forever, like our love.",
    "gem": "A gem of a day, precious and rare.",
    "crown": "King and queen of their own love story.",
    "tiara": "A tiara of dreams, princess for a day.",
    "veil": "The veil of mystery, lifted with love.",
    "glove": "A gentle touch, love at first sight.",
    "handkerchief": "Tears of joy, dabbed with love.",
    "fan": "A breeze of romance, cooling the passion.",
    "umbrella": "Under one umbrella, sharing life's storms.",
    "parasol": "A parasol of elegance, shading a radiant smile.",
    "hat": "A hat full of style, tipping towards love.",
    "bow": "A bow of gratitude, tied with love.",
    "tie": "The tie that binds, a symbol of commitment.",
    "cufflink": "Cufflinks of class, a gentleman's promise.",
    "watch": "Watching time stand still, lost in love.",
    "bell": "Bells ring out, announcing the union.",
    "saxophone": "Saxy love, smooth and soulful.",
    "violin": "Strings of the heart, playing a love song.",
    "piano": "Keys of harmony, a melody of love.",
    "guitar": "Strumming the chords of love.",
    "microphone": "Amplifying the vows, heard by all.",
    "speaker": "Love speaks volumes.",
    "camera": "Capturing the moment, freezing love in time.",
    "photo": "A photograph, a memory etched in love.",
    "album": "An album of love, pages of happiness.",
    "frame": "Framing the perfect moment.",
    "easel": "An easel of love, painting the future.",
    "painting": "A masterpiece of love, created together.",
    "sculpture": "Sculpted by love, a work of art.",
    "statue": "A statue of devotion, standing the test of time.",
    "fountain": "A fountain of youth, love keeps us young.",
    "pool": "Diving into love, deep and refreshing.",
    "lake": "A lake of serenity, reflecting love.",
    "river": "A river of love, flowing endlessly.",
    "waterfall": "A waterfall of emotions, cascading love.",
    "ocean": "An ocean of love, vast and deep.",
    "sea": "Sailing the sea of love, adventure awaits.",
    "wave": "Waves of passion, crashing on the shore of love.",
    "sand": "Footprints in the sand, a path of love.",
    "rock": "Solid as a rock, love endures.",
    "stone": "Engraved in stone, a love eternal.",
    "shell": "A shell of protection, love's safe harbor.",
    "starfish": "Starfish wishes, love from above.",
    "coral": "Coral reefs of love, colorful and vibrant.",
    "fish": "Swimming in love, free and joyful.",
    "dolphin": "Dolphins of delight, dancing in love.",
    "whale": "A whale of a love story, grand and majestic.",
    "seagull": "Seagulls soaring, love takes flight.",
    "flamingo": "Flamingos of passion, pink with love.",
    "swan": "Swans of grace, love glides smoothly.",
    "duck": "Ducks in a row, love is organized.",
    "goose": "A goose of good fortune, love brings luck.",
    "peacock": "Peacocks of pride, love displays its beauty.",
    "parrot": "Parrots of conversation, love talks.",
    "owl": "Wise owl, love sees all.",
    "eagle": "Eagle-eyed love, soaring high.",
    "hawk": "Hawk of focus, love is sharp.",
    "falcon": "Falcon of speed, love is swift.",
    "robin": "Robin of spring, love renews.",
    "sparrow": "Sparrow of simplicity, love is humble.",
    "hummingbird": "Hummingbird of energy, love is vibrant.",
    "woodpecker": "Woodpecker of persistence, love never gives up.",
    "kingfisher": "Kingfisher of patience, love waits.",
    "penguin": "Penguins of partnership, love is loyal.",
    "polar bear": "Polar bear of strength, love is powerful.",
    "bear": "Bear hug of love, warm and protective.",
    "lion": "Lion of courage, love is brave.",
    "tiger": "Tiger of passion, love is fierce.",
    "leopard": "Leopard of agility, love adapts.",
    "cheetah": "Cheetah of speed, love is quick.",
    "elephant": "Elephant of memory, love never forgets.",
    "giraffe": "Giraffe of vision, love sees far.",
    "zebra": "Zebra of uniqueness, love is one of a kind.",
    "donkey": "Donkey of determination, love carries on.",
    "cow": "Cow of contentment, love is peaceful.",
    "pig": "Pig of happiness, love is joyful.",
    "sheep": "Sheep of gentleness, love is kind.",
    "goat": "Goat of adventure, love climbs high.",
    "chicken": "Chicken of family, love is home.",
    "rooster": "Rooster of dawn, love wakes up.",
    "turkey": "Turkey of gratitude, love gives thanks.",
    "duckling": "Duckling of cuteness, love is adorable.",
    "bunny": "Bunny of softness, love is tender.",
    "rabbit": "Rabbit of luck, love is fortunate.",
    "squirrel": "Squirrel of preparation, love plans ahead.",
    "mouse": "Mouse of quietness, love is subtle.",
    "rat": "Rat of resourcefulness, love finds a way.",
    "hamster": "Hamster of energy, love is active.",
    "guinea pig": "Guinea pig of companionship, love is friendly.",
    "hedgehog": "Hedgehog of protection, love guards.",
    "porcupine": "Porcupine of defense, love shields.",
    "bat": "Bat of intuition, love senses.",
    "fox": "Fox of cleverness, love is smart.",
    "wolf": "Wolf of loyalty, love is faithful.",
    "coyote": "Coyote of adaptability, love adjusts.",
    "raccoon": "Raccoon of curiosity, love explores.",
    "skunk": "Skunk of confidence, love is bold.",
    "badger": "Badger of tenacity, love persists.",
    "otter": "Otter of playfulness, love is fun.",
    "beaver": "Beaver of building, love constructs.",
    "platypus": "Platypus of uniqueness, love is special.",
    "kangaroo": "Kangaroo of nurturing, love carries.",
    "koala": "Koala of calm, love is relaxed.",
    "wombat": "Wombat of digging, love goes deep.",
    "tasmanian devil": "Tasmanian devil of energy, love is wild.",
    "crocodile": "Crocodile of patience, love waits.",
    "alligator": "Alligator of stealth, love surprises.",
    "lizard": "Lizard of regeneration, love renews.",
    "snake": "Snake of transformation, love changes.",
    "turtle": "Turtle of longevity, love lasts.",
    "tortoise": "Tortoise of wisdom, love is slow and steady.",
    "frog": "Frog of leaps, love jumps forward.",
    "toad": "Toad of grounding, love is earthy.",
    "salamander": "Salamander of fire, love is passionate.",
    "newt": "Newt of magic, love is enchanting.",
    "dragon": "Dragon of power, love is mighty.",
    "unicorn": "Unicorn of dreams, love is magical.",
    "pegasus": "Pegasus of inspiration, love soars.",
    "phoenix": "Phoenix of rebirth, love rises.",
    "griffin": "Griffin of guardianship, love protects.",
    "mermaid": "Mermaid of mystery, love is deep.",
    "fairy": "Fairy of wishes, love grants.",
    "elf": "Elf of mischief, love is playful.",
    "gnome": "Gnome of home, love is cozy.",
    "troll": "Troll of strength, love is resilient.",
    "giant": "Giant of greatness, love is huge.",
    "ogre": "Ogre of layers, love is complex.",
    "witch": "Witch of magic, love is spellbinding.",
    "wizard": "Wizard of wisdom, love is knowledgeable.",
    "knight": "Knight of chivalry, love is honorable.",
    "princess": "Princess of grace, love is royal.",
    "prince": "Prince of charm, love is dashing.",
    "queen": "Queen of elegance, love reigns.",
    "king": "King of hearts, love rules.",
    "tower": "Tower of strength, love stands tall.",
    "bridge": "Bridge of connection, love spans gaps.",
    "gate": "Gate of opportunity, love opens doors.",
    "wall": "Wall of protection, love surrounds.",
    "moat": "Moat of reflection, love is deep.",
    "park": "Park of leisure, love strolls.",
    "forest": "Forest of mystery, love explores.",
    "jungle": "Jungle of adventure, love is wild.",
    "desert": "Desert of endurance, love survives.",
    "oasis": "Oasis of refreshment, love revives.",
    "island": "Island of escape, love is a getaway.",
    "coast": "Coast of beauty, love is scenic.",
    "cliff": "Cliff of excitement, love is thrilling.",
    "cave": "Cave of secrets, love is intimate.",
    "volcano": "Volcano of passion, love erupts.",
    "geyser": "Geyser of emotion, love bursts forth.",
    "hot spring": "Hot spring of warmth, love soothes.",
    "glacier": "Glacier of patience, love moves slowly.",
    "iceberg": "Iceberg of depth, love is more than meets the eye.",
    "aurora": "Aurora of wonder, love is magical.",
    "rainbow": "Rainbow of hope, love promises.",
    "cloud": "Cloud of dreams, love is fluffy.",
    "fog": "Fog of mystery, love is intriguing.",
    "mist": "Mist of romance, love is ethereal.",
    "dew": "Dew of freshness, love is new every morning.",
    "frost": "Frost of crispness, love is refreshing.",
    "ice": "Ice of clarity, love is transparent.",
    "snowflake": "Snowflake of uniqueness, love is one of a kind.",
    "hail": "Hail of intensity, love is powerful.",
    "storm": "Storm of passion, love is electrifying.",
    "thunder": "Thunder of excitement, love booms.",
    "lightning": "Lightning of inspiration, love strikes.",
    "tornado": "Tornado of emotion, love sweeps you away.",
    "hurricane": "Hurricane of love, wild and unstoppable.",
    "typhoon": "Typhoon of devotion, love is fierce.",
    "monsoon": "Monsoon of blessings, love pours.",
    "flood": "Flood of feelings, love overflows.",
    "drought": "Drought of longing, love thirsts.",
    "earthquake": "Earthquake of change, love shakes things up.",
    "tsunami": "Tsunami of love, overwhelming and powerful.",
    "avalanche": "Avalanche of affection, love cascades.",
    "landslide": "Landslide of commitment, love moves mountains.",
    "erosion": "Erosion of time, love endures.",
    "sediment": "Sediment of memories, love layers.",
    "fossil": "Fossil of forever, love is eternal.",
    "dinosaur": "Dinosaur of ancient love, timeless.",
    "mammoth": "Mammoth of magnitude, love is huge.",
    "saber tooth": "Saber tooth of sharpness, love is precise.",
    "caveman": "Caveman of simplicity, love is primal.",
    "campfire": "Campfire of togetherness, love gathers.",
    "bonfire": "Bonfire of celebration, love ignites.",
    "torch": "Torch of guidance, love leads the way.",
    "lantern": "Lantern of hope, love lights the path.",
    "lamp": "Lamp of warmth, love glows.",
    "chandelier": "Chandelier of elegance, love sparkles.",
    "fireplace": "Fireplace of comfort, love warms.",
    "heater": "Heater of coziness, love embraces.",
    "radiator": "Radiator of warmth, love spreads.",
    "oven": "Oven of baking, love cooks.",
    "stove": "Stove of nourishment, love feeds.",
    "grill": "Grill of flavor, love sizzles.",
    "barbecue": "Barbecue of fun, love is a feast.",
    "picnic": "Picnic of joy, love is outdoors.",
    "basket": "Basket of goodies, love is generous.",
    "blanket": "Blanket of comfort, love wraps.",
    "pillow": "Pillow of softness, love rests.",
    "mattress": "Mattress of support, love holds.",
    "bed": "Bed of dreams, love sleeps.",
    "crib": "Crib of new life, love begins.",
    "cradle": "Cradle of nurturing, love rocks.",
    "rocking chair": "Rocking chair of peace, love sways.",
    "sofa": "Sofa of relaxation, love lounges.",
    "couch": "Couch of conversation, love talks.",
    "chair": "Chair of rest, love sits.",
    "desk": "Desk of work, love supports.",
    "bookshelf": "Bookshelf of knowledge, love learns.",
    "cabinet": "Cabinet of treasures, love stores.",
    "drawer": "Drawer of secrets, love keeps.",
    "closet": "Closet of style, love dresses.",
    "wardrobe": "Wardrobe of fashion, love expresses.",
    "vase": "Vase of beauty, love arranges.",
    "bowl": "Bowl of nourishment, love serves.",
    "plate": "Plate of sharing, love dines.",
    "cup": "Cup of warmth, love sips.",
    "mug": "Mug of comfort, love holds.",
    "glass": "Glass of clarity, love toasts.",
    "bottle": "Bottle of celebration, love pops.",
    "jar": "Jar of preservation, love keeps fresh.",
    "can": "Can of convenience, love is easy.",
    "pot": "Pot of cooking, love simmers.",
    "pan": "Pan of sizzle, love fries.",
    "kettle": "Kettle of warmth, love boils.",
    "teapot": "Teapot of tradition, love steeps.",
    "coffee maker": "Coffee maker of energy, love perks.",
    "toaster": "Toaster of warmth, love pops.",
    "microwave": "Microwave of speed, love is quick.",
    "refrigerator": "Refrigerator of freshness, love cools.",
    "freezer": "Freezer of preservation, love lasts.",
    "dishwasher": "Dishwasher of cleanliness, love sparkles.",
    "washing machine": "Washing machine of renewal, love cleans.",
    "dryer": "Dryer of warmth, love fluffs.",
    "iron": "Iron of smoothness, love presses.",
    "vacuum": "Vacuum of cleanliness, love sucks up messes.",
    "broom": "Broom of sweeping, love clears.",
    "mop": "Mop of shine, love polishes.",
    "dustpan": "Dustpan of collection, love gathers.",
    "trash can": "Trash can of disposal, love lets go.",
    "recycling": "Recycling of renewal, love reuses.",
    "compost": "Compost of growth, love nourishes.",
    "garden hose": "Garden hose of life, love waters.",
    "watering can": "Watering can of care, love tends.",
    "shovel": "Shovel of digging, love plants.",
    "rake": "Rake of gathering, love collects.",
    "hoe": "Hoe of cultivation, love grows.",
    "wheelbarrow": "Wheelbarrow of transport, love carries.",
    "lawn mower": "Lawn mower of trimming, love neatens.",
    "hedge trimmer": "Hedge trimmer of shaping, love sculpts.",
    "chainsaw": "Chainsaw of power, love cuts through.",
    "axe": "Axe of splitting, love divides.",
    "hammer": "Hammer of building, love constructs.",
    "nail": "Nail of fastening, love holds.",
    "screw": "Screw of tightening, love secures.",
    "screwdriver": "Screwdriver of precision, love adjusts.",
    "wrench": "Wrench of grip, love tightens.",
    "pliers": "Pliers of hold, love grasps.",
    "drill": "Drill of penetration, love goes deep.",
    "saw": "Saw of cutting, love shapes.",
    "sandpaper": "Sandpaper of smoothing, love refines.",
    "paintbrush": "Paintbrush of creativity, love colors.",
    "paint": "Paint of expression, love art.",
    "roller": "Roller of coverage, love spreads.",
    "ladder": "Ladder of ascent, love climbs.",
    "scaffold": "Scaffold of support, love builds up.",
    "tape measure": "Tape measure of precision, love fits.",
    "level": "Level of balance, love aligns.",
    "toolbox": "Toolbox of readiness, love is prepared.",
    "hard hat": "Hard hat of protection, love guards.",
    "safety vest": "Safety vest of visibility, love is seen.",
    "gloves": "Gloves of protection, love handles.",
    "boots": "Boots of journey, love walks.",
    "shoes": "Shoes of steps, love moves.",
    "sneakers": "Sneakers of comfort, love runs.",
    "heels": "Heels of elegance, love stands tall.",
    "sandals": "Sandals of freedom, love breathes.",
    "slippers": "Slippers of comfort, love relaxes.",
    "socks": "Socks of warmth, love covers.",
    "tights": "Tights of support, love hugs.",
    "leggings": "Leggings of flexibility, love stretches.",
    "pants": "Pants of style, love dresses.",
    "jeans": "Jeans of casual, love is comfortable.",
    "shorts": "Shorts of freedom, love is breezy.",
    "skirt": "Skirt of flair, love twirls.",
    "gown": "Gown of elegance, love is formal.",
    "robe": "Robe of luxury, love wraps.",
    "jacket": "Jacket of warmth, love covers.",
    "coat": "Coat of protection, love shields.",
    "sweater": "Sweater of coziness, love knits.",
    "hoodie": "Hoodie of comfort, love is casual.",
    "shirt": "Shirt of style, love buttons.",
    "blouse": "Blouse of grace, love flows.",
    "t-shirt": "T-shirt of simplicity, love is basic.",
    "tank top": "Tank top of freedom, love is cool.",
    "bow tie": "Bow tie of charm, love is dapper.",
    "vest": "Vest of style, love layers.",
    "scarf": "Scarf of warmth, love wraps.",
    "cap": "Cap of casual, love shades.",
    "beanie": "Beanie of warmth, love covers.",
    "headband": "Headband of style, love holds.",
    "hair clip": "Hair clip of flair, love pins.",
    "hair tie": "Hair tie of hold, love secures.",
    "belt": "Belt of cinch, love holds up.",
    "suspenders": "Suspenders of support, love hangs.",
    "wallet": "Wallet of value, love holds.",
    "purse": "Purse of essentials, love carries.",
    "handbag": "Handbag of style, love totes.",
    "backpack": "Backpack of adventure, love travels.",
    "suitcase": "Suitcase of journey, love packs.",
    "briefcase": "Briefcase of business, love works.",
    "luggage": "Luggage of travel, love moves.",
    "sunglasses": "Sunglasses of cool, love shades.",
    "glasses": "Glasses of vision, love sees clearly.",
    "goggles": "Goggles of protection, love guards.",
    "bracelet": "Bracelet of charm, love adorns.",
    "necklace": "Necklace of beauty, love hangs.",
    "earrings": "Earrings of sparkle, love dangles.",
    "brooch": "Brooch of elegance, love pins.",
    "tie clip": "Tie clip of hold, love secures.",
    "keychain": "Keychain of memories, love attaches.",
    "key": "Key of access, love unlocks.",
    "lock": "Lock of security, love protects.",
    "curtain": "Curtain of privacy, love draws.",
    "blind": "Blind of shade, love filters.",
    "shutter": "Shutter of protection, love closes.",
    "roof": "Roof of shelter, love covers.",
    "chimney": "Chimney of warmth, love vents.",
    "fire escape": "Fire escape of safety, love exits.",
    "stairs": "Stairs of ascent, love climbs.",
    "elevator": "Elevator of ease, love lifts.",
    "escalator": "Escalator of movement, love steps.",
    "ramp": "Ramp of access, love slopes.",
    "hallway": "Hallway of passage, love walks.",
    "corridor": "Corridor of connection, love links.",
    "lobby": "Lobby of welcome, love greets.",
    "foyer": "Foyer of entrance, love enters.",
    "living room": "Living room of life, love dwells.",
    "family room": "Family room of togetherness, love gathers.",
    "dining room": "Dining room of meals, love feasts.",
    "kitchen": "Kitchen of creation, love cooks.",
    "bathroom": "Bathroom of refreshment, love cleanses.",
    "bedroom": "Bedroom of rest, love sleeps.",
    "pantry": "Pantry of provision, love stocks.",
    "laundry room": "Laundry room of cleanliness, love washes.",
    "garage": "Garage of storage, love parks.",
    "basement": "Basement of foundation, love grounds.",
    "attic": "Attic of memories, love stores.",
    "deck": "Deck of relaxation, love lounges.",
    "patio": "Patio of outdoors, love enjoys.",
    "porch": "Porch of welcome, love sits.",
    "balcony": "Balcony of view, love overlooks.",
    "terrace": "Terrace of elegance, love dines.",
    "yard": "Yard of play, love runs.",
    "driveway": "Driveway of arrival, love comes home.",
    "sidewalk": "Sidewalk of stroll, love walks.",
    "street": "Street of journey, love travels.",
    "road": "Road of adventure, love drives.",
    "highway": "Highway of speed, love races.",
    "freeway": "Freeway of freedom, love cruises.",
    "tunnel": "Tunnel of passage, love goes through.",
    "intersection": "Intersection of choice, love decides.",
    "crosswalk": "Crosswalk of safety, love crosses.",
    "traffic light": "Traffic light of control, love stops and goes.",
    "stop sign": "Stop sign of pause, love halts.",
    "yield sign": "Yield sign of courtesy, love gives way.",
    "speed limit": "Speed limit of caution, love slows.",
    "parking lot": "Parking lot of rest, love parks.",
    "car wash": "Car wash of cleanliness, love shines.",
    "gas station": "Gas station of fuel, love refills.",
    "charging station": "Charging station of energy, love powers up.",
    "bus stop": "Bus stop of waiting, love anticipates.",
    "train station": "Train station of departure, love leaves.",
    "airport": "Airport of travel, love flies.",
    "seaport": "Seaport of voyage, love sails.",
    "harbor": "Harbor of safety, love docks.",
    "marina": "Marina of leisure, love boats.",
    "pier": "Pier of extension, love reaches.",
    "boardwalk": "Boardwalk of stroll, love walks.",
    "spa": "Spa of relaxation, love pampers.",
    "gym": "Gym of strength, love works out.",
    "stadium": "Stadium of excitement, love cheers.",
    "arena": "Arena of competition, love plays.",
    "theater": "Theater of drama, love acts.",
    "cinema": "Cinema of stories, love watches.",
    "museum": "Museum of history, love learns.",
    "library": "Library of knowledge, love reads.",
    "school": "School of learning, love teaches.",
    "university": "University of higher learning, love grows.",
    "college": "College of experience, love matures.",
    "hospital": "Hospital of healing, love cares.",
    "clinic": "Clinic of health, love checks.",
    "pharmacy": "Pharmacy of remedy, love heals.",
    "doctor": "Doctor of care, love treats.",
    "nurse": "Nurse of compassion, love tends.",
    "dentist": "Dentist of smiles, love brightens.",
    "vet": "Vet of animals, love heals pets.",
    "police": "Police of protection, love serves.",
    "firefighter": "Firefighter of bravery, love rescues.",
    "ambulance": "Ambulance of urgency, love rushes.",
    "post office": "Post office of delivery, love sends.",
    "bank": "Bank of security, love saves.",
    "store": "Store of goods, love shops.",
    "market": "Market of variety, love chooses.",
    "supermarket": "Supermarket of plenty, love stocks.",
    "mall": "Mall of options, love browses.",
    "restaurant": "Restaurant of dining, love tastes.",
    "cafe": "Cafe of relaxation, love sips.",
    "bar": "Bar of celebration, love toasts.",
    "pub": "Pub of gathering, love chats.",
    "club": "Club of dancing, love moves.",
    "hotel": "Hotel of stay, love rests.",
    "motel": "Motel of journey, love stops.",
    "inn": "Inn of comfort, love lodges.",
    "resort": "Resort of luxury, love vacations.",
    "campground": "Campground of nature, love tents.",
    "rv park": "RV park of travel, love roams.",
    "zoo": "Zoo of animals, love observes.",
    "aquarium": "Aquarium of sea, love dives.",
    "amusement park": "Amusement park of fun, love rides.",
    "water park": "Water park of splash, love plays.",
    "circus": "Circus of wonder, love amazes.",
    "fair": "Fair of joy, love enjoys.",
    "carnival": "Carnival of excitement, love celebrates.",
    "parade": "Parade of display, love marches.",
    "festival": "Festival of culture, love experiences.",
    "concert": "Concert of music, love listens.",
    "opera": "Opera of drama, love sings.",
    "ballet": "Ballet of grace, love dances.",
    "art gallery": "Art gallery of beauty, love views.",
    "exhibition": "Exhibition of talent, love showcases.",
    "conference": "Conference of ideas, love discusses.",
    "meeting": "Meeting of minds, love agrees.",
    "office": "Office of work, love supports.",
    "factory": "Factory of production, love makes.",
    "warehouse": "Warehouse of storage, love holds.",
    "construction site": "Construction site of building, love creates.",
    "farm": "Farm of growth, love harvests.",
    "ranch": "Ranch of land, love roams.",
    "orchard": "Orchard of fruit, love picks.",
    "vineyard": "Vineyard of wine, love ferments.",
    "greenhouse": "Greenhouse of nurture, love grows.",
    "nursery": "Nursery of plants, love tends.",
    "florist": "Florist of flowers, love arranges.",
    "bakery": "Bakery of sweetness, love bakes.",
    "butcher": "Butcher of meat, love prepares.",
    "deli": "Deli of sandwiches, love makes.",
    "candy store": "Candy store of sweetness, love treats.",
    "ice cream shop": "Ice cream shop of delight, love scoops.",
    "pizzeria": "Pizzeria of sharing, love slices.",
    "food truck": "Food truck of mobility, love serves.",
    "street vendor": "Street vendor of variety, love sells.",
    "newsstand": "Newsstand of information, love reads.",
    "bookstore": "Bookstore of stories, love reads.",
    "music store": "Music store of melody, love plays.",
    "video store": "Video store of movies, love watches.",
    "game store": "Game store of fun, love plays.",
    "toy store": "Toy store of joy, love gives.",
    "clothing store": "Clothing store of style, love dresses.",
    "shoe store": "Shoe store of steps, love fits.",
    "jewelry store": "Jewelry store of sparkle, love adorns.",
    "department store": "Department store of everything, love finds.",
    "hardware store": "Hardware store of tools, love fixes.",
    "garden center": "Garden center of plants, love grows.",
    "pet store": "Pet store of companions, love adopts.",
    "bike shop": "Bike shop of cycling, love rides.",
    "car dealership": "Car dealership of vehicles, love drives.",
    "repair shop": "Repair shop of fixing, love mends.",
    "laundromat": "Laundromat of cleaning, love washes.",
    "dry cleaner": "Dry cleaner of care, love presses.",
    "tailor": "Tailor of fit, love alters.",
    "barber": "Barber of style, love cuts.",
    "hair salon": "Hair salon of beauty, love styles.",
    "nail salon": "Nail salon of polish, love shines.",
    "massage": "Massage of relief, love kneads.",
    "yoga studio": "Yoga studio of peace, love stretches.",
    "dance studio": "Dance studio of movement, love grooves.",
    "tennis court": "Tennis court of rally, love serves.",
    "basketball court": "Basketball court of hoops, love shoots.",
    "soccer field": "Soccer field of goals, love scores.",
    "baseball field": "Baseball field of diamonds, love hits.",
    "football field": "Football field of touchdowns, love tackles.",
    "golf course": "Golf course of greens, love putts.",
    "race track": "Race track of speed, love races.",
    "skate park": "Skate park of tricks, love rides.",
    "playground": "Playground of fun, love plays.",
    "trail": "Trail of hiking, love walks.",
    "bike path": "Bike path of cycling, love pedals.",
    "dock": "Dock of boats, love ties.",
    "lighthouse": "Lighthouse of guidance, love shines.",
    "cove": "Cove of seclusion, love hides.",
    "bay": "Bay of calm, love rests.",
    "canyon": "Canyon of depth, love explores.",
    "valley": "Valley of peace, love dwells.",
    "meadow": "Meadow of flowers, love blooms.",
    "field": "Field of dreams, love grows.",
    "pasture": "Pasture of grazing, love feeds.",
    "farmland": "Farmland of harvest, love reaps.",
    "woods": "Woods of mystery, love wanders.",
    "rainforest": "Rainforest of diversity, love flourishes.",
    "swamp": "Swamp of depth, love wades.",
    "marsh": "Marsh of reeds, love rustles.",
    "wetland": "Wetland of life, love teems.",
    "stream": "Stream of clarity, love babbles.",
    "creek": "Creek of quiet, love whispers.",
    "brook": "Brook of peace, love murmurs.",
    "pond": "Pond of stillness, love rests.",
    "coral reef": "Coral reef of color, love dazzles.",
    "kelp forest": "Kelp forest of sway, love dances.",
    "tide pool": "Tide pool of discovery, love finds.",
    "northern lights": "Northern lights of magic, love dances.",
    "planet": "Planet of orbit, love revolves.",
    "eclipse": "Eclipse of alignment, love meets.",
    "comet": "Comet of rarity, love streaks.",
    "meteor": "Meteor of wish, love falls.",
    "galaxy": "Galaxy of stars, love spirals.",
    "universe": "Universe of infinity, love is all.",
    "space": "Space of possibility, love explores.",
    "astronaut": "Astronaut of courage, love ventures.",
    "rocket": "Rocket of launch, love blasts off.",
    "satellite": "Satellite of orbit, love circles.",
    "telescope": "Telescope of vision, love sees far.",
    "microscope": "Microscope of detail, love examines.",
    "binoculars": "Binoculars of focus, love zooms.",
    "magnifying glass": "Magnifying glass of scrutiny, love inspects.",
    "globe": "Globe of world, love encompasses.",
    "atlas": "Atlas of places, love travels.",
    "gps": "GPS of navigation, love finds the way.",
    "hourglass": "Hourglass of sand, love flows.",
    "sundial": "Sundial of sun, love marks.",
    "calendar": "Calendar of days, love counts.",
    "planner": "Planner of organization, love schedules.",
    "notebook": "Notebook of thoughts, love writes.",
    "journal": "Journal of memories, love records.",
    "diary": "Diary of secrets, love keeps.",
    "envelope": "Envelope of delivery, love seals.",
    "stamp": "Stamp of postage, love mails.",
    "package": "Package of surprise, love delivers.",
    "box": "Box of mystery, love opens.",
    "wrapping paper": "Wrapping paper of concealment, love reveals.",
    "card": "Card of greeting, love says.",
    "announcement": "Announcement of news, love shares.",
    "certificate": "Certificate of achievement, love honors.",
    "diploma": "Diploma of graduation, love celebrates.",
    "award": "Award of recognition, love praises.",
    "trophy": "Trophy of victory, love wins.",
    "medal": "Medal of honor, love rewards.",
    "badge": "Badge of identity, love shows.",
    "patch": "Patch of belonging, love sews.",
    "sticker": "Sticker of fun, love sticks.",
    "label": "Label of information, love tags.",
    "tag": "Tag of price, love values.",
    "receipt": "Receipt of purchase, love buys.",
    "ticket": "Ticket of entry, love admits.",
    "pass": "Pass of access, love enters.",
    "membership": "Membership of belonging, love joins.",
    "license": "License of permission, love allows.",
    "permit": "Permit of authorization, love grants.",
    "passport": "Passport of travel, love goes.",
    "visa": "Visa of entry, love visits.",
    "id card": "ID card of identity, love proves.",
    "credit card": "Credit card of payment, love charges.",
    "debit card": "Debit card of funds, love spends.",
    "cash": "Cash of currency, love pays.",
    "coin": "Coin of change, love saves.",
    "bill": "Bill of money, love earns.",
    "check": "Check of payment, love writes.",
    "money clip": "Money clip of organization, love holds.",
    "safe": "Safe of security, love protects.",
    "vault": "Vault of treasure, love stores.",
    "atm": "ATM of convenience, love withdraws.",
    "piggy bank": "Piggy bank of savings, love collects.",
    "donation box": "Donation box of giving, love contributes.",
    "charity": "Charity of kindness, love gives.",
    "volunteer": "Volunteer of service, love helps.",
    "donation": "Donation of generosity, love shares.",
    "fundraiser": "Fundraiser of support, love raises.",
    "auction": "Auction of bidding, love wins.",
    "raffle": "Raffle of chance, love draws.",
    "lottery": "Lottery of luck, love wins.",
    "sweepstakes": "Sweepstakes of prize, love enters.",
    "contest": "Contest of competition, love competes.",
    "game": "Game of play, love enjoys.",
    "puzzle": "Puzzle of pieces, love fits.",
    "riddle": "Riddle of mystery, love solves.",
    "trivia": "Trivia of knowledge, love knows.",
    "quiz": "Quiz of test, love answers.",
    "exam": "Exam of assessment, love passes.",
    "test": "Test of ability, love proves.",
    "homework": "Homework of practice, love learns.",
    "project": "Project of creation, love builds.",
    "assignment": "Assignment of task, love completes.",
    "deadline": "Deadline of time, love meets.",
    "schedule": "Schedule of plan, love organizes.",
    "appointment": "Appointment of meeting, love keeps.",
    "reservation": "Reservation of hold, love books.",
    "booking": "Booking of arrangement, love confirms.",
    "order": "Order of request, love places.",
    "subscription": "Subscription of renewal, love continues.",
    "account": "Account of profile, love logs in.",
    "profile": "Profile of identity, love shows.",
    "avatar": "Avatar of representation, love appears.",
    "username": "Username of identity, love logs.",
    "password": "Password of security, love protects.",
    "login": "Login of access, love enters.",
    "logout": "Logout of exit, love leaves.",
    "sign up": "Sign up of registration, love joins.",
    "sign in": "Sign in of return, love comes back.",
    "settings": "Settings of preference, love adjusts.",
    "preferences": "Preferences of choice, love selects.",
    "options": "Options of variety, love chooses.",
    "menu": "Menu of selection, love picks.",
    "toolbar": "Toolbar of tools, love uses.",
    "dashboard": "Dashboard of overview, love sees.",
    "home page": "Home page of start, love begins.",
    "website": "Website of presence, love visits.",
    "web page": "Web page of content, love reads.",
    "link": "Link of connection, love clicks.",
    "hyperlink": "Hyperlink of jump, love goes.",
    "url": "URL of address, love types.",
    "domain": "Domain of name, love owns.",
    "hosting": "Hosting of server, love runs.",
    "server": "Server of data, love stores.",
    "cloud": "Cloud of storage, love saves.",
    "download": "Download of transfer, love gets.",
    "upload": "Upload of sharing, love gives.",
    "stream": "Stream of flow, love watches.",
    "buffer": "Buffer of wait, love loads.",
    "loading": "Loading of patience, love waits.",
    "progress bar": "Progress bar of completion, love fills.",
    "error": "Error of mistake, love fixes.",
    "bug": "Bug of glitch, love debugs.",
    "crash": "Crash of failure, love restarts.",
    "reboot": "Reboot of refresh, love starts anew.",
    "update": "Update of improvement, love upgrades.",
    "upgrade": "Upgrade of better, love enhances.",
    "install": "Install of setup, love begins.",
    "uninstall": "Uninstall of removal, love cleans.",
    "setup": "Setup of configuration, love prepares.",
    "wizard": "Wizard of guidance, love leads.",
    "tutorial": "Tutorial of learning, love teaches.",
    "guide": "Guide of help, love shows.",
    "manual": "Manual of instruction, love reads.",
    "faq": "FAQ of questions, love answers.",
    "help": "Help of support, love assists.",
    "support": "Support of care, love helps.",
    "customer service": "Customer service of assistance, love serves.",
    "contact": "Contact of reach, love connects.",
    "email": "Email of message, love sends.",
    "message": "Message of communication, love talks.",
    "chat": "Chat of conversation, love chats.",
    "text": "Text of words, love types.",
    "call": "Call of voice, love speaks.",
    "phone": "Phone of connection, love dials.",
    "smartphone": "Smartphone of smart, love holds.",
    "tablet": "Tablet of touch, love swipes.",
    "laptop": "Laptop of portable, love works.",
    "desktop": "Desktop of station, love sits.",
    "computer": "Computer of power, love computes.",
    "keyboard": "Keyboard of input, love types.",
    "mouse": "Mouse of click, love points.",
    "trackpad": "Trackpad of glide, love moves.",
    "monitor": "Monitor of display, love sees.",
    "screen": "Screen of view, love watches.",
    "printer": "Printer of output, love prints.",
    "scanner": "Scanner of copy, love digitizes.",
    "fax": "Fax of old, love sends.",
    "copier": "Copier of duplicate, love copies.",
    "shredder": "Shredder of destroy, love disposes.",
    "stapler": "Stapler of bind, love attaches.",
    "hole punch": "Hole punch of holes, love organizes.",
    "paper clip": "Paper clip of hold, love clips.",
    "binder clip": "Binder clip of grip, love holds.",
    "rubber band": "Rubber band of stretch, love binds.",
    "tape": "Tape of stick, love adheres.",
    "glue": "Glue of bond, love sticks.",
    "scissors": "Scissors of cut, love snips.",
    "cutter": "Cutter of slice, love trims.",
    "knife": "Knife of sharp, love cuts.",
    "blade": "Blade of edge, love slices.",
    "sword": "Sword of battle, love fights.",
    "shield": "Shield of defense, love protects.",
    "armor": "Armor of protection, love guards.",
    "helmet": "Helmet of safety, love covers.",
    "gun": "Gun of power, love shoots.",
    "rifle": "Rifle of aim, love targets.",
    "pistol": "Pistol of hand, love holds.",
    "bullet": "Bullet of speed, love flies.",
    "cannon": "Cannon of boom, love fires.",
    "bomb": "Bomb of explosion, love blasts.",
    "grenade": "Grenade of throw, love explodes.",
    "missile": "Missile of launch, love strikes.",
    "tank": "Tank of armor, love rolls.",
    "helicopter": "Helicopter of rotor, love hovers.",
    "jet": "Jet of speed, love zooms.",
    "spaceship": "Spaceship of stars, love travels.",
    "submarine": "Submarine of deep, love dives.",
    "ship": "Ship of sea, love sails.",
    "yacht": "Yacht of luxury, love cruises.",
    "canoe": "Canoe of paddle, love rows.",
    "kayak": "Kayak of stream, love paddles.",
    "raft": "Raft of river, love floats.",
    "surfboard": "Surfboard of wave, love rides.",
    "sailboat": "Sailboat of wind, love sails.",
    "motorboat": "Motorboat of engine, love speeds.",
    "jetski": "Jetski of splash, love zooms.",
    "tricycle": "Tricycle of three, love rolls.",
    "unicycle": "Unicycle of balance, love rides.",
    "scooter": "Scooter of zip, love goes.",
    "skateboard": "Skateboard of trick, love flips.",
    "roller skates": "Roller skates of glide, love rolls.",
    "ice skates": "Ice skates of glide, love slides.",
    "skis": "Skis of snow, love glides.",
    "snowboard": "Snowboard of slope, love carves.",
    "sled": "Sled of hill, love slides.",
    "toboggan": "Toboggan of snow, love races.",
    "snowmobile": "Snowmobile of winter, love rides.",
    "atv": "ATV of trail, love rides.",
    "go kart": "Go kart of race, love speeds.",
    "race car": "Race car of track, love races.",
    "formula 1": "Formula 1 of speed, love wins.",
    "nascar": "NASCAR of oval, love circles.",
    "monster truck": "Monster truck of crush, love smashes.",
    "tractor": "Tractor of farm, love plows.",
    "bulldozer": "Bulldozer of push, love moves.",
    "excavator": "Excavator of dig, love scoops.",
    "crane": "Crane of lift, love raises.",
    "forklift": "Forklift of stack, love lifts.",
    "dump truck": "Dump truck of load, love dumps.",
    "cement mixer": "Cement mixer of mix, love pours.",
    "fire truck": "Fire truck of emergency, love responds.",
    "police car": "Police car of patrol, love serves.",
    "taxi": "Taxi of ride, love hails.",
    "bus": "Bus of transport, love rides.",
    "school bus": "School bus of children, love carries.",
    "trolley": "Trolley of street, love rolls.",
    "tram": "Tram of city, love travels.",
    "subway": "Subway of underground, love goes.",
    "monorail": "Monorail of future, love glides.",
    "cable car": "Cable car of hill, love climbs.",
    "gondola": "Gondola of canal, love rows.",
    "ferry": "Ferry of water, love crosses.",
    "cruise ship": "Cruise ship of vacation, love sails.",
    "cargo ship": "Cargo ship of goods, love transports.",
    "container ship": "Container ship of boxes, love ships.",
    "oil tanker": "Oil tanker of fuel, love carries.",
    "fishing boat": "Fishing boat of catch, love nets.",
    "tugboat": "Tugboat of pull, love guides.",
    "barge": "Barge of river, love floats.",
    "houseboat": "Houseboat of living, love dwells.",
    "pontoon": "Pontoon of leisure, love lounges.",
    "catamaran": "Catamaran of speed, love sails.",
    "trimaran": "Trimaran of stability, love cruises.",
    "hovercraft": "Hovercraft of air, love glides.",
    "airboat": "Airboat of swamp, love skims.",
    "seaplane": "Seaplane of water, love lands.",
    "floatplane": "Floatplane of lake, love touches down.",
    "drone": "Drone of sky, love flies.",
    "hot air balloon": "Hot air balloon of float, love rises.",
    "blimp": "Blimp of air, love drifts.",
    "zeppelin": "Zeppelin of history, love travels.",
    "parachute": "Parachute of fall, love floats.",
    "paraglider": "Paraglider of soar, love flies.",
    "hang glider": "Hang glider of wind, love glides.",
    "wingsuit": "Wingsuit of flight, love dives.",
    "jetpack": "Jetpack of future, love flies.",
    "rocket pack": "Rocket pack of power, love blasts.",
    "space shuttle": "Space shuttle of orbit, love launches.",
    "space station": "Space station of home, love lives.",
    "rover": "Rover of Mars, love explores.",
    "lander": "Lander of moon, love touches down.",
    "probe": "Probe of deep space, love ventures.",
    "observatory": "Observatory of sky, love watches.",
    "planetarium": "Planetarium of stars, love shows.",
    "laboratory": "Laboratory of science, love experiments.",
    "chemistry": "Chemistry of reaction, love bonds.",
    "physics": "Physics of forces, love attracts.",
    "biology": "Biology of life, love grows.",
    "geology": "Geology of earth, love rocks.",
    "astronomy": "Astronomy of stars, love gazes.",
    "meteorology": "Meteorology of weather, love forecasts.",
    "oceanography": "Oceanography of sea, love dives.",
    "ecology": "Ecology of environment, love sustains.",
    "botany": "Botany of plants, love grows.",
    "zoology": "Zoology of animals, love studies.",
    "genetics": "Genetics of inheritance, love passes on.",
    "medicine": "Medicine of healing, love cures.",
    "surgery": "Surgery of operation, love fixes.",
    "nursing": "Nursing of care, love tends.",
    "dentistry": "Dentistry of teeth, love smiles.",
    "veterinary": "Veterinary of animals, love heals.",
    "psychology": "Psychology of mind, love understands.",
    "psychiatry": "Psychiatry of mental health, love helps.",
    "therapy": "Therapy of healing, love talks.",
    "counseling": "Counseling of guidance, love advises.",
    "social work": "Social work of help, love serves.",
    "education": "Education of learning, love teaches.",
    "teaching": "Teaching of knowledge, love imparts.",
    "tutoring": "Tutoring of help, love guides.",
    "training": "Training of skill, love develops.",
    "coaching": "Coaching of motivation, love inspires.",
    "mentoring": "Mentoring of wisdom, love shares.",
    "parenting": "Parenting of raising, love nurtures.",
    "childcare": "Childcare of watching, love cares.",
    "babysitting": "Babysitting of temporary, love sits.",
    "nannying": "Nannying of full-time, love raises.",
    "eldercare": "Eldercare of respect, love honors.",
    "caregiving": "Caregiving of compassion, love tends.",
    "nursing home": "Nursing home of care, love resides.",
    "assisted living": "Assisted living of help, love supports.",
    "hospice": "Hospice of comfort, love eases.",
    "funeral": "Funeral of goodbye, love mourns.",
    "cemetery": "Cemetery of rest, love remembers.",
    "grave": "Grave of final, love lays.",
    "tombstone": "Tombstone of memory, love marks.",
    "mausoleum": "Mausoleum of grandeur, love entombs.",
    "cremation": "Cremation of ash, love scatters.",
    "urn": "Urn of remains, love holds.",
    "memorial": "Memorial of honor, love remembers.",
    "obituary": "Obituary of life, love writes.",
    "eulogy": "Eulogy of praise, love speaks.",
    "condolences": "Condolences of sympathy, love offers.",
    "sympathy": "Sympathy of understanding, love feels.",
    "empathy": "Empathy of sharing, love connects.",
    "compassion": "Compassion of kindness, love acts.",
    "kindness": "Kindness of heart, love gives.",
    "generosity": "Generosity of spirit, love shares.",
    "gratitude": "Gratitude of thanks, love appreciates.",
    "appreciation": "Appreciation of value, love recognizes.",
    "thank you": "Thank you of gratitude, love says.",
    "you're welcome": "You're welcome of politeness, love responds.",
    "please": "Please of request, love asks.",
    "sorry": "Sorry of apology, love regrets.",
    "excuse me": "Excuse me of pardon, love moves.",
    "hello": "Hello of greeting, love meets.",
    "goodbye": "Goodbye of parting, love leaves.",
    "welcome": "Welcome of arrival, love greets.",
    "congratulations": "Congratulations of achievement, love celebrates.",
    "happy birthday": "Happy birthday of celebration, love wishes.",
    "happy anniversary": "Happy anniversary of milestone, love commemorates.",
    "merry christmas": "Merry Christmas of holiday, love shares.",
    "happy new year": "Happy New Year of beginning, love starts.",
    "happy easter": "Happy Easter of spring, love renews.",
    "happy halloween": "Happy Halloween of spooky, love treats.",
    "happy thanksgiving": "Happy Thanksgiving of gratitude, love feasts.",
    "happy valentine's day": "Happy Valentine's Day of love, love celebrates.",
    "happy mother's day": "Happy Mother's Day of mom, love honors.",
    "happy father's day": "Happy Father's Day of dad, love appreciates.",
    "happy graduation": "Happy Graduation of achievement, love celebrates.",
    "happy retirement": "Happy Retirement of rest, love congratulates.",
    "get well soon": "Get well soon of health, love wishes.",
    "good luck": "Good luck of fortune, love wishes.",
    "best wishes": "Best wishes of hope, love sends.",
    "thinking of you": "Thinking of you of care, love remembers.",
    "missing you": "Missing you of longing, love yearns.",
    "i love you": "I love you of affection, love declares.",
    "love": "Love of all, love is.",
}

# Fallback captions if no class matches
FALLBACK_CAPTIONS = [
    "A beautiful moment filled with love and joy.",
    "Cherished memories, captured forever.",
    "Love in every glance, joy in every smile.",
    "A day to remember, a love to last a lifetime.",
    "Happiness is love, and love is all around.",
    "Every picture tells a story of love.",
    "A snapshot of pure bliss and romance.",
    "Love shines brightest in the simplest moments.",
    "Together is a wonderful place to be.",
    "A perfect day, a perfect love.",
]


def generate_caption_rpi5(image_bytes: bytes) -> str:
    """Generate a wedding-themed caption using MobileNetV2 classification (RPi5 optimized)."""
    import numpy as np
    from PIL import Image

    interpreter, labels = _load_caption_classifier()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    # Preprocess image: resize to 224x224, keep as uint8 [0,255]
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB').resize((224, 224))
    img_array = np.array(img, dtype=np.uint8)
    img_array = np.expand_dims(img_array, axis=0)

    interpreter.set_tensor(input_details[0]['index'], img_array)
    interpreter.invoke()
    predictions = interpreter.get_tensor(output_details[0]['index'])[0]

    # Get top-5 predicted class indices
    top_indices = np.argsort(predictions)[-5:][::-1]

    # Try to find a matching caption template
    for idx in top_indices:
        class_name = labels[idx].lower().replace('_', ' ').strip()
        # Check for exact match or substring match
        for key, caption in CAPTION_TEMPLATES.items():
            if key in class_name or class_name in key:
                return caption
        # Also check if any word in class_name matches a key
        for word in class_name.split():
            if word in CAPTION_TEMPLATES:
                return CAPTION_TEMPLATES[word]

    # Fallback: pick a random romantic caption
    import random
    return random.choice(FALLBACK_CAPTIONS)


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
