"""Quick script to view recent synthetic posts."""
import sqlite3

conn = sqlite3.connect('c:/Career/CSE881/BladeRunner/Data/Scraped/scraper.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT platform, model, text_length, text 
    FROM synthetic_posts 
    ORDER BY id DESC 
    LIMIT 5
''')

posts = cursor.fetchall()

print("\n" + "="*80)
print("RECENT SYNTHETIC POSTS (showing diversity from improved prompting)")
print("="*80)

for i, (platform, model, length, text) in enumerate(posts, 1):
    print(f"\n{i}. [{platform.upper()}] via {model} | {length} chars")
    print("-" * 80)
    print(text)
    print("="*80)

conn.close()
