import sqlite3
import pandas as pd

# Connect to your existing database
conn = sqlite3.connect('scraper.db')

# Load the posts into a Pandas DataFrame
df = pd.read_sql_query("SELECT * FROM posts", conn)

print("=== DATA COLLECTION STATS (For Report) ===")
print(f"Total Posts Collected: {len(df)}")
print("\nPosts by Platform:")
print(df['platform'].value_counts())

print("\nList of Attributes Collected:")
print(list(df.columns))

print("\n=== DATA PREPROCESSING ISSUES (For Report) ===")
print("Missing Data (Null Values):")
# Show columns that have missing data
missing = df.isnull().sum()
print(missing[missing > 0])

# Check for empty strings in the text column
empty_text = len(df[df['text'].str.strip() == ''])
print(f"\nPosts with empty text fields: {empty_text}")

# Get average length of posts per platform to highlight formatting differences
print("\nAverage character length by platform:")
df['text_length'] = df['text'].str.len()
print(df.groupby('platform')['text_length'].mean())

print("\n=== GENERATING SAMPLE POSTS FOR AI PROMPTS ===")
# Filter out any posts with empty text to ensure high-quality prompts
valid_posts = df[df['text'].astype(str).str.strip() != '']

# Grab up to 15 random Reddit posts
reddit_samples = valid_posts[valid_posts['platform'] == 'reddit']
reddit_sampled = reddit_samples.sample(n=min(15, len(reddit_samples)), random_state=42)

# Grab up to 15 random Bluesky posts
bsky_samples = valid_posts[valid_posts['platform'] == 'bluesky']
bsky_sampled = bsky_samples.sample(n=min(15, len(bsky_samples)), random_state=42)

# Combine them, keeping only the platform and the text columns
samples_df = pd.concat([reddit_sampled, bsky_sampled])[['platform', 'text']]

# Save to CSV in the same folder
output_file = 'prompt_samples.csv'
samples_df.to_csv(output_file, index=False)

print(f"✅ Successfully saved {len(samples_df)} sample posts to: {output_file}")
print("You can now open 'prompt_samples.csv' and copy the text directly into ChatGPT/Gemini!")

conn.close()