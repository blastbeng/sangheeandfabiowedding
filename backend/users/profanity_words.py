"""
Profanity word lists for content moderation.
Used to filter inappropriate language in user-submitted text fields.
"""

import re

# English profanity words
PROFANITY_WORDS_EN = [
    "asshole",
    "bastard",
    "bitch",
    "cock",
    "crap",
    "cunt",
    "damn",
    "dick",
    "fuck",
    "motherfucker",
    "nigga",
    "nigger",
    "piss",
    "shit",
    "slut",
    "whore",
]

# Italian profanity words
PROFANITY_WORDS_IT = [
    "cazzo",
    "coglione",
    "culattone",
    "figa",
    "merda",
    "porca",
    "puttana",
    "stronzo",
    "troia",
    "vaffanculo",
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
]

# Combined set for all languages (lowercased for case-insensitive matching)
PROFANITY_WORDS = set(
    word.lower() for word in PROFANITY_WORDS_EN + PROFANITY_WORDS_IT + PROFANITY_WORDS_KO
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
