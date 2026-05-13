"""
Profanity word lists for content moderation.
Used to filter inappropriate language in user-submitted text fields.
"""

import re

# English profanity words
PROFANITY_WORDS_EN = [
    "ass",
    "asshole",
    "bastard",
    "bitch",
    "bollocks",
    "bugger",
    "cock",
    "crap",
    "cunt",
    "damn",
    "dick",
    "dickhead",
    "douche",
    "douchebag",
    "fag",
    "faggot",
    "fuck",
    "fucker",
    "motherfucker",
    "nigga",
    "nigger",
    "piss",
    "prick",
    "pussy",
    "shit",
    "slut",
    "twat",
    "wanker",
    "whore",
]

# Italian profanity words
PROFANITY_WORDS_IT = [
    "bastardo",
    "cazzo",
    "coglione",
    "cornuto",
    "culattone",
    "figa",
    "frocio",
    "merda",
    "minchia",
    "negro",
    "porca",
    "puttana",
    "ricchione",
    "stronzo",
    "troia",
    "vaffanculo",
    "zoccola",
]

# Korean profanity words (Hangul)
PROFANITY_WORDS_KO = [
    "씨발",
    "개새끼",
    "병신",
    "좆",
    "보지",
    "자지",
    "염병",
    "지랄",
    "미친놈",
    "미친년",
    "쌍놈",
    "쌍년",
    "또라이",
    "걸레",
    "창녀",
    "호로",
    "새끼",
    "니애미",
    "니기미",
    "좆까",
]

# Spanish profanity words
PROFANITY_WORDS_ES = [
    "cabron",
    "cabrón",
    "carajo",
    "chinga",
    "chingada",
    "chingar",
    "cojones",
    "coño",
    "culero",
    "joder",
    "jodido",
    "maldito",
    "marica",
    "maricón",
    "mierda",
    "pendejo",
    "perra",
    "pinche",
    "puta",
    "puto",
    "verga",
    "zorra",
]

# French profanity words
PROFANITY_WORDS_FR = [
    "batard",
    "bâtard",
    "bite",
    "bordel",
    "chatte",
    "connard",
    "connasse",
    "con",
    "cul",
    "enculé",
    "encule",
    "foutre",
    "merde",
    "nique",
    "niquer",
    "pétasse",
    "pute",
    "putain",
    "salaud",
    "salope",
    "ta gueule",
    "trou du cul",
]

# Portuguese profanity words
PROFANITY_WORDS_PT = [
    "bicha",
    "boceta",
    "bosta",
    "burro",
    "caralho",
    "cu",
    "foda",
    "foder",
    "fodido",
    "merda",
    "pau",
    "porra",
    "puta",
    "puto",
    "quenga",
    "safado",
    "vaca",
    "viado",
    "xota",
]

# Combined set for all languages (lowercased for case-insensitive matching)
PROFANITY_WORDS = set(
    word.lower() for word in (
        PROFANITY_WORDS_EN +
        PROFANITY_WORDS_IT +
        PROFANITY_WORDS_KO +
        PROFANITY_WORDS_ES +
        PROFANITY_WORDS_FR +
        PROFANITY_WORDS_PT
    )
)


def contains_profanity(text):
    """
    Check if the given text contains any profanity words.

    Uses word-boundary matching for Latin scripts and simple substring
    matching for non-Latin scripts (e.g., Korean) to avoid false positives.

    Args:
        text: The text to check. Can be None or empty.

    Returns:
        bool: True if profanity is found, False otherwise.
    """
    if not text:
        return False

    text_lower = text.lower()
    for profanity in PROFANITY_WORDS:
        # For Latin-based words, use word boundaries to reduce false positives
        if profanity.isascii():
            pattern = r'\b' + re.escape(profanity) + r'\b'
            if re.search(pattern, text_lower):
                return True
        else:
            # For non-Latin scripts (Korean, etc.), use simple substring match
            if profanity in text_lower:
                return True
    return False
