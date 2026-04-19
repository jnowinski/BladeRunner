import os
import json 
from data_loader import load_and_split_data
from text_cleaner import clean_text
from tokenizer import get_models, generate_embeddings # Updated imports
from clean_database import CleanDatabaseManager

def process_and_store(df, split_name, tokenizer, model, clean_db):
    print(f"\nProcessing {split_name.upper()} split ({len(df)} rows)...")

    print("  -> Applying text cleaning...")
    df['cleaned_text'] = df['text'].apply(clean_text)
    df = df[df['cleaned_text'].str.len() > 0].copy()

    # Pass the model in alongside the tokenizer
    input_ids, attention_masks, embeddings = generate_embeddings(
        df['cleaned_text'].tolist(), tokenizer, model
    )
    
    print("  -> Saving to cleaned_data database...")
    records = []
    for i, row in enumerate(df.itertuples()):
        records.append((
            row.post_id,
            row.text,
            row.cleaned_text,
            row.label,
            split_name,
            json.dumps(input_ids[i]),
            json.dumps(attention_masks[i]),
            json.dumps(embeddings[i]) # Include the new embeddings array
        ))
    
    # Update the SQL string to include the embeddings column
    insert_sql = """
    INSERT OR REPLACE INTO cleaned_posts 
    (post_id, original_text, cleaned_text, label, split_group, input_ids, attention_mask, embeddings)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    with clean_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(insert_sql, records)
        
    print(f"✅ {split_name.upper()} complete.")

if __name__ == "__main__":
    print("=== Starting Clean Track Pipeline ===")

    print("Setting up cleaned_data database...")
    clean_db = CleanDatabaseManager()
    clean_db.create_tables()

    train_df, val_df, test_df = load_and_split_data()

    print("Downloading/Loading DistilBERT Tokenizer and Model...")
    # Load both the tokenizer and the network
    tokenizer, model = get_models()

    process_and_store(train_df, "train", tokenizer, model, clean_db)
    process_and_store(val_df, "val", tokenizer, model, clean_db)
    process_and_store(test_df, "test", tokenizer, model, clean_db)

    print("\n🎉 Pipeline Finished! Clean Track is fully complete.")