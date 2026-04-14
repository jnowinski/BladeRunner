import os
import sqlite3
import pandas as pd
import json

# 1. Locate the database
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
db_path = os.path.join(project_root, 'Data', 'Processed', 'cleaned_data.db')

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    print("Please make sure you have run main.py to generate the clean data.")
    exit()

print(f"Connecting to database at: {db_path}")
conn = sqlite3.connect(db_path)

# 2. Count total records
cursor = conn.cursor()
try:
    cursor.execute("SELECT count(*) FROM cleaned_posts")
    total_posts = cursor.fetchone()[0]
    print(f"\nTotal posts currently in cleaned database: {total_posts}")
    print("-" * 50)
except sqlite3.OperationalError as e:
    print(f"\nError reading table: {e}")
    total_posts = 0

# 3. Fetch and display the first 5 rows
if total_posts > 0:
    df = pd.read_sql("SELECT * FROM cleaned_posts LIMIT 5", conn)
    
    # Helper function to summarize massive JSON arrays for terminal viewing
    def summarize_array(json_str):
        if not json_str:
            return "None"
        try:
            arr = json.loads(json_str)
            return f"[Array of {len(arr)} items]"
        except:
            return "[Invalid JSON]"

    # Apply the summary function to the heavy transformer columns
    if 'input_ids' in df.columns:
        df['input_ids'] = df['input_ids'].apply(summarize_array)
    if 'attention_mask' in df.columns:
        df['attention_mask'] = df['attention_mask'].apply(summarize_array)
    if 'embeddings' in df.columns:
        df['embeddings'] = df['embeddings'].apply(summarize_array)

    # Clean up display settings so Pandas prints a nice wide table
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    
    print("\nFirst 5 rows of the 'cleaned_posts' table:")
    print(df.head())
else:
    print("\nThe 'cleaned_posts' table is currently empty!")

# Always close the connection
conn.close()