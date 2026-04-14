import sys
import os
import pandas as pd
from sklearn.model_selection import train_test_split

# 1. Navigate up to the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# 2. INTERCEPT THE CONFIG: Force the absolute path
from Scraper.config import DATABASE_CONFIG

db_folder = os.path.join(project_root, 'Data', 'Scraped')

# Handle the scraped.db vs scraper.db naming quirk
if os.path.exists(os.path.join(db_folder, 'scraped.db')):
    DATABASE_CONFIG['db_path'] = os.path.join(db_folder, 'scraped.db')
else:
    DATABASE_CONFIG['db_path'] = os.path.join(db_folder, 'scraper.db')

# 3. Import DatabaseManager
from Scraper.database import DatabaseManager, Post

def load_and_split_data():
    """Pulls scraped data from SQLite, labels as Human, and splits 70/15/15."""
    print(f"Connecting to database at: {DATABASE_CONFIG['db_path']}")
    db = DatabaseManager()
    
    with db.get_session() as session:
        # Pull ALL posts, since we are only working with the raw scraped data right now
        posts = session.query(Post).all()
        
        data = []
        for p in posts:
            data.append({
                'post_id': p.post_id,
                'text': p.text,
                'category': 'human_written', # Explicitly label them for our pipeline
                'label': 0                   # 0 = Human class
            })

    # Safety Check
    if not data:
        raise ValueError("CRITICAL: The database returned 0 posts. Check your database path.")

    df = pd.DataFrame(data)
    
    # Drop rows with missing text (empty posts will crash DistilBERT)
    df.dropna(subset=['text'], inplace=True)
    
    print(f"Total normal posts loaded: {len(df)}")
    print("Executing standard 70/15/15 split...")

    # First split: 70% Train, 30% Temp
    # Removed 'stratify' since we currently only have one class of data
    train_df, temp_df = train_test_split(
        df, test_size=0.30, random_state=42
    )

    # Second split: Cut Temp in half for 15% Val, 15% Test
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, random_state=42
    )

    return train_df, val_df, test_df