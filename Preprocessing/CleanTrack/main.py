import os
from data_loader import load_and_split_data
from text_cleaner import clean_text
from tokenizer import get_tokenizer, tokenize_texts
from clean_database import CleanDatabaseManager, CleanPost

def process_and_store(df, split_name, tokenizer, clean_db):
    """Cleans, tokenizes, and saves the data directly into the new SQLAlchemy DB."""
    print(f"\nProcessing {split_name.upper()} split ({len(df)} rows)...")

    # 1. Clean the text
    print("  -> Applying text cleaning...")
    df['cleaned_text'] = df['text'].apply(clean_text)

    # Drop any posts that became empty strings after cleaning
    df = df[df['cleaned_text'].str.len() > 0].copy()

    # 2. Tokenize
    print("  -> Generating DistilBERT tokens...")
    input_ids, attention_masks = tokenize_texts(df['cleaned_text'].tolist(), tokenizer)
    
    # 3. Save to the new SQLAlchemy database
    print("  -> Saving to cleaned_data database...")
    
    records = []
    for i, row in enumerate(df.itertuples()):
        # Create a new SQLAlchemy CleanPost object for every row
        records.append(CleanPost(
            post_id=row.post_id,
            original_text=row.text,
            cleaned_text=row.cleaned_text,
            label=row.label,
            split_group=split_name, # Tags it as 'train', 'val', or 'test'
            input_ids=input_ids[i],
            attention_mask=attention_masks[i]
        ))
    
    # Bulk insert is much faster than adding them one by one
    with clean_db.get_session() as session:
        session.bulk_save_objects(records)
        
    print(f"✅ {split_name.upper()} complete.")

if __name__ == "__main__":
    print("=== Starting Clean Track Pipeline ===")

    # Step A: Initialize the NEW database schema
    print("Setting up cleaned_data database...")
    clean_db = CleanDatabaseManager()
    clean_db.create_tables()

    # Step B: Load and Split Data (reads from the ORIGINAL scraper.db)
    train_df, val_df, test_df = load_and_split_data()

    # Step C: Initialize Tokenizer
    print("Downloading/Loading DistilBERT Tokenizer...")
    tokenizer = get_tokenizer()

    # Step D: Process each split and save securely to the new DB
    process_and_store(train_df, "train", tokenizer, clean_db)
    process_and_store(val_df, "val", tokenizer, clean_db)
    process_and_store(test_df, "test", tokenizer, clean_db)

    print("\n🎉 Pipeline Finished! Original database is untouched, and clean data is safely stored.")