from transformers import DistilBertTokenizer

def get_tokenizer():
    """Initializes and returns the DistilBERT tokenizer."""
    return DistilBertTokenizer.from_pretrained('distilbert-base-uncased')

def tokenize_texts(texts, tokenizer):
    """
    Tokenizes a list of strings. 
    Returns lists of integers so they can be easily saved to Parquet.
    """
    encodings = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors=None # Returns lists instead of pt tensors for Parquet compatibility
    )
    
    return encodings['input_ids'], encodings['attention_mask']