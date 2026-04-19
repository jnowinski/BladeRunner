import torch
from transformers import DistilBertTokenizer, DistilBertModel
from tqdm import tqdm

def get_models():
    """Initializes and returns the DistilBERT tokenizer and model."""
    tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
    model = DistilBertModel.from_pretrained('distilbert-base-uncased')
    model.eval() # Set model to evaluation mode (turns off training mechanics)
    return tokenizer, model

def generate_embeddings(texts, tokenizer, model, batch_size=32):
    """Tokenizes text and generates dense vector embeddings in batches."""
    all_input_ids = []
    all_masks = []
    all_embeddings = []

    # Process in batches with a progress bar
    for i in tqdm(range(0, len(texts), batch_size), desc="Generating Embeddings"):
        batch_texts = texts[i:i+batch_size]

        # Tokenize (using PyTorch tensors this time)
        inputs = tokenizer(
            batch_texts, 
            padding=True, 
            truncation=True, 
            max_length=512, 
            return_tensors="pt"
        )

        # Run the model without calculating gradients to save memory
        with torch.no_grad():
            outputs = model(**inputs)

        # We take the [CLS] token (index 0) as the embedding for the entire post
        batch_embeddings = outputs.last_hidden_state[:, 0, :].tolist()

        # Store the results
        all_input_ids.extend(inputs['input_ids'].tolist())
        all_masks.extend(inputs['attention_mask'].tolist())
        all_embeddings.extend(batch_embeddings)
        
    return all_input_ids, all_masks, all_embeddings