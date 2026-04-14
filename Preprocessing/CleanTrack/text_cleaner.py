import re

# Dictionary for contraction expansion
CONTRACTIONS = {
    "don't": "do not", "can't": "cannot", "won't": "will not",
    "it's": "it is", "i'm": "i am", "you're": "you are",
    "they're": "they are", "we're": "we are", "isn't": "is not",
    "aren't": "are not", "wasn't": "was not", "weren't": "were not"
}

def clean_text(text):
    """Cleans text for Transformer embeddings."""
    if not isinstance(text, str):
        return ""
        
    # 1. Lowercase
    text = text.lower()
    
    # 2. Expand contractions
    for contraction, expansion in CONTRACTIONS.items():
        text = text.replace(contraction, expansion)
        
    # 3. Remove URLs
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    
    # 4. Remove Mentions (e.g., @username)
    text = re.sub(r'@\w+', '', text)
    
    # 5. Remove punctuation and special characters (keep alphanumeric and spaces)
    text = re.sub(r'[^\w\s]', '', text)
    
    # 6. Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text