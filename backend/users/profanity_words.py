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

# Combined set for all languages (lowercased for case-insensitive matching)
PROFANITY_WORDS = set(
    word.lower() for word in PROFANITY_WORDS_EN + PROFANITY_WORDS_IT
)


def contains_profanity(text):
    """
    Check if the given text contains any profanity words.

    Uses word-boundary matching to reduce false positives
    (e.g., "classic" won't match "ass").

    Args:
        text: The text to check. Can be None or empty.

    Returns:
        bool: True if profanity is found, False otherwise.
    """
    if not text:
        return False

    text_lower = text.lower()
    for profanity in PROFANITY_WORDS:
        pattern = r'\b' + re.escape(profanity) + r'\b'
        if re.search(pattern, text_lower):
            return True
    return False
