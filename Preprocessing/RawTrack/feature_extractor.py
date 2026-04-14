import torch
import math
import re
import numpy as np
import nltk
from transformers import GPT2LMHeadModel, GPT2TokenizerFast

# Ensure NLTK tokenizers are downloaded silently
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)

class StylometricExtractor:
    def __init__(self):
        print("Loading GPT-2 for Perplexity calculations...")
        self.tokenizer = GPT2TokenizerFast.from_pretrained('gpt2')
        self.model = GPT2LMHeadModel.from_pretrained('gpt2')
        self.model.eval() # Evaluation mode

    def calculate_perplexity(self, text):
        """Calculates how 'surprised' GPT-2 is by the text. Lower = more AI-like."""
        # Truncate to GPT-2's max window to prevent crashes on massive posts
        encodings = self.tokenizer(text, return_tensors='pt', max_length=1024, truncation=True)
        input_ids = encodings.input_ids

        if input_ids.size(1) == 0:
            return 0.0

        with torch.no_grad():
            outputs = self.model(input_ids, labels=input_ids)
            loss = outputs.loss
            
        return math.exp(loss.item())

    def calculate_burstiness(self, text):
        """Variance in sentence length. High variance = more human-like."""
        sentences = nltk.sent_tokenize(text)
        if not sentences:
            return 0.0
            
        lengths = [len(nltk.word_tokenize(sentence)) for sentence in sentences]
        return float(np.var(lengths))

    def calculate_punctuation_density(self, text):
        """Ratio of non-alphanumeric characters to total characters."""
        if not text:
            return 0.0
        
        # Find all characters that are NOT word characters or whitespace
        punct_chars = re.findall(r'[^\w\s]', text)
        return len(punct_chars) / len(text)

    def calculate_lexical_diversity(self, text):
        """Type-Token Ratio: Unique words divided by total words."""
        words = nltk.word_tokenize(text.lower())
        
        # Filter out purely punctuation "words" parsed by NLTK
        words = [w for w in words if w.isalnum()]
        
        if not words:
            return 0.0
            
        unique_words = set(words)
        return len(unique_words) / len(words)

    def extract_all(self, text):
        """Wrapper to return all 4 metrics at once."""
        return {
            'perplexity': self.calculate_perplexity(text),
            'burstiness': self.calculate_burstiness(text),
            'punctuation_density': self.calculate_punctuation_density(text),
            'lexical_diversity': self.calculate_lexical_diversity(text)
        }