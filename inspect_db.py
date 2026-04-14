import pandas as pd
from Scraper.database import DatabaseManager, Post

print("Connecting to database...")
# Initialize the connection using your existing setup
db = DatabaseManager()

# Open a session using the context manager your teammate built
with db.get_session() as session:
    
    # 1. Let's see how many total posts are currently in the database
    total_posts = session.query(Post).count()
    print(f"\nTotal posts currently in database: {total_posts}")
    print("-" * 50)
    
    # 2. Query the first 5 posts to inspect the data
    recent_posts = session.query(Post).limit(5).all()
    
    # 3. Convert the SQLAlchemy objects into a list of dictionaries
    posts_data = []
    for post in recent_posts:
        # Get the dictionary representation of the SQLAlchemy object
        post_dict = post.__dict__.copy()
        # Remove the internal SQLAlchemy state key so it doesn't clutter our output
        post_dict.pop('_sa_instance_state', None) 
        posts_data.append(post_dict)
    
    # 4. Load into Pandas just to make it print out beautifully in the terminal
    if posts_data:
        df = pd.DataFrame(posts_data)
        # Force pandas to show all columns instead of truncating them with "..."
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        
        print("\nFirst 5 rows of the 'posts' table:")
        print(df.head())
    else:
        print("\nThe 'posts' table is currently empty!")