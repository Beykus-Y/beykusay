import re

def contains_bad_words(text: str) -> bool:
    bad_patterns = {
        # r'\b(?:спам|реклам)\b',
        # r'\b(?:мат[а-я]*|руган)\b',
        # r'\b(?:http|https|t\.me|@)\b'
    }
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in bad_patterns)