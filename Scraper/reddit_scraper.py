"""
Reddit scraper using PRAW (Python Reddit API Wrapper).
"""
import logging
from typing import List, Any, Optional
from datetime import datetime

import praw

from base_scraper import BaseScraper
from database import DatabaseManager
from utils import RateLimiter
from config import REDDIT_CONFIG, SCRAPER_CONFIG


class RedditScraper(BaseScraper):
    """Scraper for Reddit using PRAW."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize Reddit scraper."""
        super().__init__('reddit', db_manager)
        self.reddit = None
        self.rate_limiter = RateLimiter(
            max_requests=self.max_requests,
            period=self.period
        )
    
    def authenticate(self) -> bool:
        """
        Authenticate with Reddit API.
        
        Returns:
            True if authentication successful
        """
        try:
            client_id = REDDIT_CONFIG['client_id']
            client_secret = REDDIT_CONFIG['client_secret']
            user_agent = REDDIT_CONFIG['user_agent']
            
            if not all([client_id, client_secret, user_agent]):
                logging.error("Reddit API credentials not configured")
                return False
            
            # Initialize PRAW Reddit instance
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )
            
            # Test authentication
            # PRAW doesn't require explicit auth check for read-only operations
            # But we can test by accessing a subreddit
            self.reddit.subreddit('test').id
            
            self.authenticated = True
            logging.info("Reddit authentication successful")
            return True
            
        except Exception as e:
            logging.error(f"Reddit authentication failed: {e}")
            self.authenticated = False
            return False
    
    def fetch_posts(self, query: str = None, since_id: str = None,
                   since_time: datetime = None, max_results: int = 100) -> List[Any]:
        """
        Fetch posts from Reddit.
        
        Args:
            query: Subreddit name (without r/) or search query
            since_id: Not used for Reddit (uses timestamp instead)
            since_time: Fetch posts after this timestamp
            max_results: Maximum number of posts to fetch
        
        Returns:
            List of submission objects
        """
        if not self.authenticated:
            logging.error("Not authenticated with Reddit")
            return []
        
        try:
            # Apply rate limiting
            self.rate_limiter.wait_if_needed()
            
            submissions = []
            
            if not query:
                logging.warning("No subreddit/query provided for Reddit scraper")
                return []
            
            # Determine if query is a subreddit or search term
            # If it contains spaces or special characters, treat as search
            if ' ' in query or any(char in query for char in [':', '"', 'OR', 'AND']):
                # Search across Reddit
                logging.info(f"Searching Reddit for: {query}")
                results = self.reddit.subreddit('all').search(query, limit=max_results, sort='new')
                submissions = list(results)
            else:
                # Treat as subreddit name
                logging.info(f"Fetching from subreddit: r/{query}")
                subreddit = self.reddit.subreddit(query)
                
                # Fetch new posts from subreddit
                submissions = list(subreddit.new(limit=max_results))
            
            # Filter by timestamp if provided (for incremental scraping)
            if since_time:
                since_timestamp = since_time.timestamp()
                submissions = [
                    s for s in submissions 
                    if s.created_utc > since_timestamp
                ]
            
            logging.info(f"Fetched {len(submissions)} Reddit posts")
            return submissions
            
        except praw.exceptions.PRAWException as e:
            logging.error(f"Reddit API error: {e}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error fetching Reddit posts: {e}")
            return []
    
    def fetch_comments(self, submission_id: str, max_comments: int = 50) -> List[Any]:
        """
        Fetch comments from a specific submission.
        
        Args:
            submission_id: Reddit submission ID
            max_comments: Maximum number of comments to fetch
        
        Returns:
            List of comment objects
        """
        if not self.authenticated:
            logging.error("Not authenticated with Reddit")
            return []
        
        try:
            submission = self.reddit.submission(id=submission_id)
            
            # Expand comment tree
            submission.comments.replace_more(limit=0)
            
            # Get top-level comments
            comments = list(submission.comments)[:max_comments]
            
            logging.info(f"Fetched {len(comments)} comments from submission {submission_id}")
            return comments
            
        except Exception as e:
            logging.error(f"Error fetching Reddit comments: {e}")
            return []
