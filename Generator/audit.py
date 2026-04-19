"""
Enhanced data analysis script for scraped social media posts.
Exports comprehensive statistics and prepares sample pool for synthetic generation.
"""
import sqlite3
import pandas as pd
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from Scraper.config import DATABASE_CONFIG

# Connect to database
db_path = DATABASE_CONFIG['db_path']
print(f"Connecting to database: {db_path}")
conn = sqlite3.connect(db_path)

# Load the posts into a Pandas DataFrame
df = pd.read_sql_query("SELECT * FROM posts", conn)

print("\n" + "="*80)
print("=== DATA COLLECTION STATS ===")
print("="*80)
print(f"Total Posts Collected: {len(df):,}")
print(f"Date Range: {df['created_at'].min()} to {df['created_at'].max()}")

print("\nPosts by Platform:")
platform_counts = df['platform'].value_counts()
for platform, count in platform_counts.items():
    print(f"  {platform:15} {count:,} posts ({count/len(df)*100:.1f}%)")

print("\nAttributes Collected:")
print(f"  Columns: {', '.join(df.columns)}")

print("\n" + "="*80)
print("=== DATA QUALITY ANALYSIS ===")
print("="*80)

# Missing data analysis
print("Missing Data (Null Values):")
missing = df.isnull().sum()
has_missing = missing[missing > 0]
if len(has_missing) > 0:
    for col, count in has_missing.items():
        print(f"  {col:15} {count:,} missing ({count/len(df)*100:.1f}%)")
else:
    print("  ✅ No missing values!")

# Text quality checks
df['text'] = df['text'].fillna('')  # Replace NaN with empty string
df['text_length'] = df['text'].str.len()

empty_text = len(df[df['text'].str.strip() == ''])
print(f"\nPosts with empty text: {empty_text:,} ({empty_text/len(df)*100:.1f}%)")

# Length distribution
print("\nText Length Statistics by Platform:")
length_stats = df.groupby('platform')['text_length'].agg(['count', 'mean', 'median', 'min', 'max'])
print(length_stats.to_string())

print("\n" + "="*80)
print("=== PREPARING SAMPLE POOL FOR GENERATION ===")
print("="*80)

# Quality filters for sample pool
MIN_TEXT_LENGTH = 10  # Minimum characters
MAX_TEXT_LENGTH = 1000  # Maximum characters

valid_posts = df[
    (df['text'].astype(str).str.strip() != '') &  # Non-empty
    (df['text_length'] >= MIN_TEXT_LENGTH) &       # Minimum length
    (df['text_length'] <= MAX_TEXT_LENGTH)         # Maximum length
].copy()

print(f"Quality Filters Applied:")
print(f"  - Non-empty text")
print(f"  - Minimum {MIN_TEXT_LENGTH} characters")
print(f"  - Maximum {MAX_TEXT_LENGTH} characters")
print(f"\nValid Posts: {len(valid_posts):,} ({len(valid_posts)/len(df)*100:.1f}% of total)")

# Show counts by platform
print("\nValid Posts by Platform:")
valid_platform_counts = valid_posts['platform'].value_counts()
for platform, count in valid_platform_counts.items():
    print(f"  {platform:15} {count:,} posts")

# Prepare sample pool export (metadata only - samples will be loaded from DB during generation)
sample_pool_metadata = {
    'total_samples': len(valid_posts),
    'platforms': {platform: int(count) for platform, count in valid_platform_counts.items()},
    'generated_at': datetime.now().isoformat(),
    'min_length': MIN_TEXT_LENGTH,
    'max_length': MAX_TEXT_LENGTH,
    'length_stats': {
        'mean': float(valid_posts['text_length'].mean()),
        'median': float(valid_posts['text_length'].median()),
        'min': int(valid_posts['text_length'].min()),
        'max': int(valid_posts['text_length'].max()),
    },
    'database_path': db_path,
    'quality_filters': {
        'min_text_length': MIN_TEXT_LENGTH,
        'max_text_length': MAX_TEXT_LENGTH,
        'non_empty': True,
    }
}

# Export metadata only
output_json = Path(__file__).parent / 'sample_pool_metadata.json'
with open(output_json, 'w', encoding='utf-8') as f:
    json.dump(sample_pool_metadata, f, indent=2, ensure_ascii=False)

print(f"\n✅ Sample pool metadata exported to: {output_json}")
print(f"   Total valid samples: {len(valid_posts):,}")
print(f"   (Samples will be loaded directly from database during generation)")

# Create a small random sample for preview/testing (100 posts)
preview_sample = valid_posts.sample(n=min(100, len(valid_posts)), random_state=42)
preview_data = []
for idx, row in preview_sample.iterrows():
    preview_data.append({
        'platform': row['platform'],
        'text': row['text'],
        'text_length': int(row['text_length']),
    })

output_preview_json = Path(__file__).parent / 'sample_preview.json'
with open(output_preview_json, 'w', encoding='utf-8') as f:
    json.dump(preview_data, f, indent=2, ensure_ascii=False)

print(f"✅ Preview sample exported to: {output_preview_json}")
print(f"   Preview samples: {len(preview_data):,}")

print("\n" + "="*80)
print("=== SUMMARY ===")
print("="*80)
print(f"Total scraped posts:  {len(df):,}")
print(f"Valid sample pool:    {len(valid_posts):,}")
print(f"Ready for generation: ✅")
print("="*80)

conn.close()