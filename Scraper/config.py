"""
Configuration settings for the social media scraper.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file at project root
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

# Database Configuration
DATABASE_CONFIG = {
    'db_path': os.getenv('DB_PATH', str(project_root / 'Data' / 'Scraped' / 'scraper.db')),
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

# ========================================
# Synthetic Data Generation API Configurations
# ========================================

# Azure OpenAI Configuration (GPT-5-mini, GPT-4.1-nano)
AZURE_OPENAI_CONFIG = {
    'api_key': os.getenv('AZURE_OPENAI_API_KEY'),
    'endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),  # e.g., https://{resource}.openai.azure.com/
    'api_version': os.getenv('AZURE_OPENAI_API_VERSION', '2024-08-01-preview'),
    'deployments': {
        'gpt54_nano': os.getenv('AZURE_GPT54_NANO_DEPLOYMENT', 'gpt-5.4-nano'),
        'gpt41_mini': os.getenv('AZURE_GPT41_MINI_DEPLOYMENT', 'gpt-4.1-mini'),
    },
}

# Anthropic Claude Configuration
CLAUDE_CONFIG = {
    'api_key': os.getenv('CLAUDE_API_KEY'),
    'model': os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022'),
}

# Google Gemini Configuration
GEMINI_CONFIG = {
    'api_key': os.getenv('GEMINI_API_KEY'),
    'model': os.getenv('GEMINI_MODEL', 'gemini-1.5-flash'),
}

# Groq Configuration (for Llama)
GROQ_CONFIG = {
    'api_key': os.getenv('GROQ_API_KEY'),
    'model': os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile'),
}

# DeepSeek Configuration
DEEPSEEK_CONFIG = {
    'api_key': os.getenv('DEEPSEEK_API_KEY'),
    'model': os.getenv('DEEPSEEK_MODEL', 'deepseek-chat'),
    'base_url': os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
}

# Generation Configuration
GENERATION_CONFIG = {
    # Model distribution (must sum to 100)
    'model_distribution': {
        'gpt54_nano': 33.0,     # GPT-5.4-nano (Azure)
        'gpt41_mini': 33.0,     # GPT-4.1-mini (Azure)
        'claude': 20.0,         # Claude Sonnet 4-6
        'gemini': 0.0,          # Gemini 2.5 Flash (disabled)
        'llama': 14.0,          # Llama 4 Scout via Groq
        'deepseek': 0.0,        # DeepSeek-V3 (disabled)
    },
    
    # Few-shot prompt configuration
    'samples_per_prompt': 12,  # Number of real examples to include per generation
    
    # Budget and safety limits
    'max_budget_usd': 50,       # Hard cap on spending
    'cost_per_1k_tracking': True,
    
    # Batch processing settings
    'use_batch_when_available': True,
    'batch_wait_timeout_hours': 48,
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
            # Software Development & AI Coding
            'vibecoding OR "vibe coding"',
            '"AI generated code" OR "ChatGPT code" OR "Copilot code"',
            '"coding with AI" OR "AI pair programming"',
            '"10x engineer" OR "10x developer"',
            'leetcode OR "coding interview" OR "tech interview"',
            '#100DaysOfCode OR "learning to code"',
            '"junior developer" OR "bootcamp graduate"',
            'webdev OR "web development" OR frontend OR backend',
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
            # Software Development (High AI Usage)
            'learnprogramming',
            'webdev',
            'cscareerquestions',
            'experienceddevs',
            'coding',
            'codinghelp',
            'leetcode',
            'csMajors',
            'webdevelopment',
            'javascript',
            'python',
            'react',
            'node',
            'Frontend',
            'Backend',
            'devops',
            'softwareengineering',
            'ProgrammerHumor',
            'badcode',
            'programminghorror',
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
            # Software Development & AI Coding
            'vibecoding',
            'vibe coding',
            'AI generated code',
            'coding with AI',
            'ChatGPT code',
            'GitHub Copilot',
            'AI pair programming',
            '10x engineer',
            'coding interview',
            'tech interview',
            'leetcode',
            '100DaysOfCode',
            'learning to code',
            'bootcamp',
            'junior developer',
            'web development',
            'webdev',
            'frontend',
            'backend',
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
