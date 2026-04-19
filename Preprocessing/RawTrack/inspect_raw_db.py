import os
import sqlite3
import pandas as pd

# 1. Locate the database
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
db_path = os.path.join(project_root, 'Data', 'Processed', 'raw_data.db')

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    print("Please make sure you have run main.py in the RawTrack folder to generate the features.")
    exit()

print(f"Connecting to database at: {db_path}")
conn = sqlite3.connect(db_path)

# 2. Count total records
cursor = conn.cursor()
try:
    cursor.execute("SELECT count(*) FROM raw_features")
    total_posts = cursor.fetchone()[0]
    print(f"\nTotal posts currently in raw database: {total_posts}")
    print("-" * 50)
except sqlite3.OperationalError as e:
    print(f"\nError reading table: {e}")
    total_posts = 0

# 3. Fetch and display the first 5 rows
if total_posts > 0:
    df = pd.read_sql("SELECT * FROM raw_features LIMIT 5", conn)
    
    # Clean up display settings so Pandas prints a nice wide table
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    
    print("\nFirst 5 rows of the 'raw_features' table:")
    print(df.head())
else:
    print("\nThe 'raw_features' table is currently empty!")

# Always close the connection
conn.close()