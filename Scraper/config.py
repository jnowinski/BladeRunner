"""
Configuration settings for the social media scraper.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database Configuration
DATABASE_CONFIG = {
    'db_path': os.getenv('DB_PATH', '../Data/Scraped/scraper.db'),
}

# Twitter/X API Configuration
TWITTER_CONFIG = {
    'bearer_token': os.getenv('TWITTER_BEARER_TOKEN'),
}

# Reddit API Configuration
REDDIT_CONFIG = {
    'client_id': os.getenv('REDDIT_CLIENT_ID'),
    'client_secret': os.getenv('REDDIT_CLIENT_SECRET'),
    'user_agent': os.getenv('REDDIT_USER_AGENT', 'SocialMediaScraper/1.0'),
}

# Bluesky API Configuration
BLUESKY_CONFIG = {
    'handle': os.getenv('BLUESKY_HANDLE'),
    'app_password': os.getenv('BLUESKY_APP_PASSWORD'),
}

# Threads API Configuration (Optional)
THREADS_CONFIG = {
    'access_token': os.getenv('THREADS_ACCESS_TOKEN'),
}

# Scraper Configuration
SCRAPER_CONFIG = {
    # Poll intervals in minutes
    'poll_intervals': {
        'twitter': 7,     # 5-10 minutes recommended
        'reddit': 12,     # 10-15 minutes recommended
        'bluesky': 7,     # 5-10 minutes recommended
        'threads': 15,    # Placeholder for future
    },
    
    # Search queries - flexible configuration
    # Format: {'platform': ['query1', 'query2', ...]}
    'search_queries': {
        'twitter': [
            # Technology & AI
            'AI OR "Machine Learning" OR "Artificial Intelligence"',
            'ChatGPT OR GPT OR "large language models"',
            'Python programming',
            # News & Current Events
            'breaking news',
            'world news',
            # Arts & Culture
            'digital art OR illustration',
            'photography',
            'music OR musicians',
            # Literature & Writing
            'books OR reading OR literature',
            'creative writing',
            # Entertainment
            'movies OR cinema',
            'gaming OR videogames',
            'TV shows OR television',
            # AI-Prone Content (advice, stories, viral posts)
            'AITA OR "am I the asshole"',
            'relationship advice',
            'life advice OR "life pro tips"',
            'confession OR confessions',
            'unpopular opinion',
            'story time OR storytime',
        ],
        'reddit': [
            # Technology & AI
            'machinelearning',
            'artificial',
            'technology',
            'programming',
            'datascience',
            # News
            'news',
            'worldnews',
            'technology',
            # Arts
            'Art',
            'DigitalArt',
            'drawing',
            'photography',
            'Music',
            'listentothis',
            # Literature
            'books',
            'literature',
            'writing',
            'booksuggestions',
            'WritingPrompts',
            'shortscarystories',
            # Entertainment
            'movies',
            'television',
            'gaming',
            'entertainment',
            # General Interest
            'todayilearned',
            'science',
            'space',
            'history',
            'Documentaries',
            # AI-Prone Content (advice, stories, Q&A)
            'AmItheAsshole',
            'relationship_advice',
            'tifu',
            'confession',
            'nosleep',
            'explainlikeimfive',
            'AskReddit',
            'legaladvice',
            'LifeProTips',
            'UnpopularOpinion',
            'changemyview',
            'TwoSentenceHorror',
            'AskScience',
            'AskHistorians',
        ],
        'bluesky': [
            # Technology & AI
            'AI',
            'Machine Learning',
            'technology',
            'programming',
            # News
            'breaking news',
            'world news',
            'politics',
            # Arts & Culture
            'art',
            'digital art',
            'photography',
            'music',
            # Literature
            'books',
            'reading',
            'writing',
            'poetry',
            'creative writing',
            'short stories',
            # Entertainment
            'movies',
            'film',
            'gaming',
            'television',
            # Science & Education
            'science',
            'space',
            'history',
            # AI-Prone Content (advice, stories, forums)
            'advice',
            'life advice',
            'relationship advice',
            'AITA',
            'am I the asshole',
            'confession',
            'true stories',
            'horror stories',
            'ask me anything',
            'explain like',
            'life pro tips',
            'unpopular opinion',
        ],
    },
    
    # Rate limit configurations (requests per period)
    'rate_limits': {
        'twitter': {'requests': 450, 'period': 900},   # 450 req per 15 min
        'reddit': {'requests': 60, 'period': 60},      # 60 req per 1 min
        'bluesky': {'requests': 3000, 'period': 300},  # 3000 req per 5 min
    },
    
    # Maximum retries for failed requests
    'max_retries': 3,
    
    # Exponential backoff base (seconds)
    'backoff_base': 60,
    
    # Maximum posts to fetch per scrape iteration
    'max_posts_per_fetch': 100,
}

# Logging Configuration
LOGGING_CONFIG = {
    'log_dir': 'logs',
    'log_file': 'scraper.log',
    'log_level': 'INFO',
    'max_bytes': 10 * 1024 * 1024,  # 10 MB
    'backup_count': 5,
}

# Daemon Configuration
DAEMON_CONFIG = {
    'pid_file': 'scraper.pid',
    'state_file': 'scraper_state.json',
}
