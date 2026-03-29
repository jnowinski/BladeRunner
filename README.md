# Multi-Platform Social Media Scraper

A Python-based scraper for collecting posts from Twitter/X, Reddit, Bluesky, and Threads. Features continuous monitoring with scheduled polling, SQLite storage, and graceful start/stop controls.

## Features

- **Multi-Platform Support**: Twitter/X, Reddit, Bluesky (Threads stub for future)
- **Continuous Monitoring**: Daemon mode with scheduled polling
- **Incremental Scraping**: Only fetch new posts since last run
- **Unified Data Schema**: Normalized storage across all platforms
- **SQLite Storage**: Git-friendly, team-shareable, optimized for classification
- **Rate Limiting**: Automatic rate limit handling with exponential backoff
- **Graceful Shutdown**: Save state on stop, resume from checkpoint
- **Flexible Configuration**: Keywords, hashtags, subreddits via config file

## Architecture

```
Scraper/
├── config.py              # Configuration settings
├── database.py            # SQLAlchemy models and DatabaseManager
├── base_scraper.py        # Abstract base class for scrapers
├── normalizer.py          # Data normalization across platforms
├── utils.py               # Rate limiting, logging, helpers
├── twitter_scraper.py     # Twitter/X implementation (Tweepy)
├── reddit_scraper.py      # Reddit implementation (PRAW)
├── bluesky_scraper.py     # Bluesky implementation (atproto)
├── threads_scraper.py     # Threads stub (future)
├── scraper_manager.py     # Orchestrator with APScheduler
├── daemon.py              # Daemon lifecycle management
└── scraper.py             # Main CLI entry point
```

## Setup

### 1. Prerequisites

- Python 3.8+
- API credentials for each platform
- (SQLite is built into Python - no database server needed!)

### 2. Install Dependencies

```bash
cd Scraper
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Database Setup

**Good news**: SQLite database is created automatically!

The database file will be created at `data/scraper.db` on first run.

**To share data with team**: Just commit the .db file to Git!

```bash
git add data/scraper.db
git commit -m "Add scraped data"
git push
```

Team members can `git pull` to get your data instantly.

### 4. Configure API Credentials

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```bash
# Twitter/X - Get from developer.twitter.com
TWITTER_BEARER_TOKEN=your_bearer_token_here

# Reddit - Get from reddit.com/prefs/apps
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=YourBotName/1.0

# Bluesky - Create app password at bsky.app/settings/app-passwords
BLUESKY_HANDLE=your_handle.bsky.social
BLUESKY_APP_PASSWORD=your_app_password_here

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=social_scraper
DB_USER=postgres
DB_PASSWORD=your_password_here
```

### 5. Configure Search Queries

Edit `config.py` to customize search queries and poll intervals:

```python
SCRAPER_CONFIG = {
    'poll_intervals': {
        'twitter': 7,     # minutes
        'reddit': 12,
        'bluesky': 7,
    },
    
    'search_queries': {
        'twitter': [
            'AI OR "Machine Learning"',
            'Python programming',
        ],
        'reddit': [
            'machinelearning',  # subreddit name
            'Python',
        ],
        'bluesky': [
            'AI',
            'Machine Learning',
        ],
    },
}
```

## Usage

### Start Scraping

```bash
# Start all configured platforms
python scraper.py start

# Start specific platforms only
python scraper.py start --platforms twitter reddit bluesky
```

### Check Status

```bash
python scraper.py status
```

Output:
```
============================================================
SCRAPER DAEMON STATUS
============================================================
Status:       RUNNING
PID:          12345
Last Updated: 2026-03-24 10:30:00

Statistics:
  Total Scrapes:      42
  Successful Scrapes: 40
  Failed Scrapes:     2
  Total Posts:        1,523
  Uptime:             2:15:30

Log File:     logs/scraper.log
State File:   scraper_state.json
============================================================
```

### Stop Scraping

```bash
python scraper.py stop
```

### Restart Scraping

```bash
python scraper.py restart
```

## API Credential Setup

### Twitter/X

1. Go to [developer.twitter.com](https://developer.twitter.com)
2. Create a new app (or use existing)
3. Navigate to "Keys and tokens"
4. Copy **Bearer Token**
5. Add to `.env`: `TWITTER_BEARER_TOKEN=...`

**Rate Limits**: 450 requests per 15 minutes (free tier)

### Reddit

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click "Create App" or "Create Another App"
3. Select "script" type
4. Copy **client_id** (under app name) and **client_secret**
5. Add to `.env`:
   ```
   REDDIT_CLIENT_ID=...
   REDDIT_CLIENT_SECRET=...
   REDDIT_USER_AGENT=YourBotName/1.0
   ```

**Rate Limits**: 60 requests per minute

### Bluesky

1. Go to [bsky.app/settings/app-passwords](https://bsky.app/settings/app-passwords)
2. Click "Add App Password"
3. Give it a name (e.g., "Scraper")
4. Copy the generated password
5. Add to `.env`:
   ```
   BLUESKY_HANDLE=yourhandle.bsky.social
   BLUESKY_APP_PASSWORD=...
   ```

**Rate Limits**: 3,000 requests per 5 minutes

## Data Schema

All posts are normalized to a common schema:

```sql
posts (
    post_id,              -- Platform-specific ID
    platform,             -- twitter, reddit, bluesky
    text,                 -- Full post text
    author_username,      -- Author handle
    created_at,           -- Post timestamp
    like_count,           -- Engagement metrics
    reply_count,
    retweet_count,
    ...
    raw_json              -- Original platform response
)
```

Hashtags are stored in a separate table for efficient filtering:

```sql
post_hashtags (
    post_id,
    hashtag
)
```

## Querying Data

### Using SQLite Command Line

```bash
sqlite3 data/scraper.db
```

```sql
-- Get all posts from last 24 hours
SELECT platform, author_username, text, created_at
FROM posts
WHERE created_at > datetime('now', '-24 hours')
ORDER BY created_at DESC;

-- Count posts by platform
SELECT platform, COUNT(*) as post_count
FROM posts
GROUP BY platform;

-- Find posts with specific hashtag
SELECT p.text, p.author_username, p.created_at
FROM posts p
JOIN post_hashtags h ON p.id = h.post_id
WHERE h.hashtag = 'ai'
ORDER BY p.created_at DESC;
```

### Using Python/Pandas

```python
import pandas as pd
import sqlite3

conn = sqlite3.connect('data/scraper.db')
df = pd.read_sql('SELECT * FROM posts', conn)

# Export to CSV for classification
df.to_csv('posts_for_classification.csv', index=False)
```

## Troubleshooting

### Authentication Errors

- **Twitter**: Verify Bearer Token is valid and not expired
- **Reddit**: Check client_id/client_secret are correct
- **Bluesky**: Ensure app password (not main password) is used

### Database Errors

```bash
# Verify database file exists
ls data/scraper.db

# Check database integrity
sqlite3 data/scraper.db "PRAGMA integrity_check;"
```

If corrupted, delete and let scraper recreate:
```bash
rm data/scraper.db
python scraper.py start
```

### No Posts Being Collected

1. Check logs: `tail -f logs/scraper.log`
2. Verify search queries in `config.py` match platform syntax
3. Check rate limits haven't been exceeded

### Daemon Won't Start

1. Check if already running: `python scraper.py status`
2. Remove stale PID file: `rm scraper.pid`
3. Check logs for errors: `tail -n 50 logs/scraper.log`

## Logs

All scraping activity is logged to `logs/scraper.log` with rotation (10MB max, 5 backups).

```bash
# View recent logs
tail -f logs/scraper.log

# Search for errors
grep ERROR logs/scraper.log

# View specific platform activity
grep "twitter" logs/scraper.log
```

## State Persistence

The scraper saves its state to `scraper_state.json`:
- Last scrape timestamps per platform/query
- Statistics (posts collected, scrapes run, etc.)
- Automatically restored on restart

This enables:
- **Incremental scraping**: Only fetch new posts
- **Resume after crash**: Continue from last checkpoint
- **No duplicate posts**: Unique constraint on post_id + platform

## Extending

### Add a New Platform

1. Create `your_platform_scraper.py` inheriting from `BaseScraper`
2. Implement `authenticate()` and `fetch_posts()`
3. Add normalizer in `normalizer.py`
4. Register in `scraper_manager.py`
5. Add config in `config.py`

### Add Classification

The scraper provides clean data. To add classification:

```python
import pandas as pd
import sqlite3

# Read posts from database
conn = sqlite3.connect('data/scraper.db')
df = pd.read_sql('SELECT text, platform, created_at FROM posts', conn)

# Your classification code here
# ...

# Save predictions back to database
cursor = conn.cursor()
cursor.execute('UPDATE posts SET sentiment = ?, category = ? WHERE id = ?', 
               (sentiment, category, post_id))
conn.commit()
```

## License

This project is for educational/research purposes. Ensure compliance with each platform's Terms of Service.

---

**Need Help?**
- Check logs: `logs/scraper.log`
- View status: `python scraper.py status`
- Restart if stuck: `python scraper.py restart`
