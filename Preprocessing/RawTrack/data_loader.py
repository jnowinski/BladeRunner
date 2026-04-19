import os
import sqlite3
import pandas as pd

def load_synchronized_data():
    """Pulls the original text and split groups directly from the Clean Track database."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    clean_db_path = os.path.join(project_root, 'Data', 'Processed', 'cleaned_data.db')
    
    if not os.path.exists(clean_db_path):
        raise FileNotFoundError(f"Cannot find Clean Track DB at {clean_db_path}. Run Clean Track first.")

    print(f"Connecting to Clean Track database to synchronize splits...")
    conn = sqlite3.connect(clean_db_path)
    
    # We only need the ID, the raw text, the label, and what split it belongs to
    query = "SELECT post_id, original_text, label, split_group FROM cleaned_posts"
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Drop rows where original_text is somehow missing
    df.dropna(subset=['original_text'], inplace=True)
    
    return df