import os
from tqdm import tqdm
from data_loader import load_synchronized_data
from feature_extractor import StylometricExtractor
from raw_database import RawDatabaseManager

def process_raw_track():
    print("=== Starting Raw Track Pipeline ===")
    
    # 1. Setup Database
    raw_db = RawDatabaseManager()
    raw_db.create_tables()
    
    # 2. Load Synchronized Data
    df = load_synchronized_data()
    print(f"Loaded {len(df)} posts from Clean Track.")
    
    # 3. Initialize Extractor
    extractor = StylometricExtractor()
    
    # 4. Extract Features
    records = []
    print("\nExtracting stylometric features...")
    
    # Iterate through dataframe with a progress bar
    for row in tqdm(df.itertuples(), total=len(df), desc="Processing Posts"):
        text = str(row.original_text)
        features = extractor.extract_all(text)
        
        records.append((
            row.post_id,
            row.split_group,
            row.label,
            features['perplexity'],
            features['burstiness'],
            features['punctuation_density'],
            features['lexical_diversity']
        ))
        
    # 5. Save to Database
    print("\nSaving features to raw_data database...")
    insert_sql = """
    INSERT OR REPLACE INTO raw_features 
    (post_id, split_group, label, perplexity, burstiness, punctuation_density, lexical_diversity)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    
    with raw_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(insert_sql, records)
        
    print("🎉 Raw Track is fully complete! Features are stored and synchronized.")

if __name__ == "__main__":
    process_raw_track()