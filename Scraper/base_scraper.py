"""
Base abstract scraper class that all platform scrapers inherit from.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from database import DatabaseManager, ScraperState
from normalizer import DataNormalizer
from utils import retry_with_backoff
from config import SCRAPER_CONFIG


class BaseScraper(ABC):
    """Abstract base class for all platform scrapers."""
    
    def __init__(self, platform: str, db_manager: DatabaseManager):
        """
        Initialize base scraper.
        
        Args:
            platform: Platform name (twitter, reddit, bluesky, threads)
            db_manager: DatabaseManager instance
        """
        self.platform = platform
        self.db_manager = db_manager
        self.normalizer = DataNormalizer()
        self.authenticated = False
        
        # Rate limiting configuration
        rate_config = SCRAPER_CONFIG['rate_limits'].get(platform, {})
        self.max_requests = rate_config.get('requests', 100)
        self.period = rate_config.get('period', 60)
        
        logging.info(f"Initialized {platform} scraper")
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the platform API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        pass
    
    @abstractmethod
    def fetch_posts(self, query: str = None, since_id: str = None, 
                   since_time: datetime = None, max_results: int = 100) -> List[Any]:
        """
        Fetch posts from the platform.
        
        Args:
            query: Search query (keywords, hashtags, subreddit name, etc.)
            since_id: Fetch posts after this ID (for incremental scraping)
            since_time: Fetch posts after this timestamp
            max_results: Maximum number of posts to fetch
        
        Returns:
            List of raw post objects from platform API
        """
        pass
    
    def normalize_data(self, raw_posts: List[Any]) -> List[Dict[str, Any]]:
        """
        Normalize raw posts to unified schema.
        
        Args:
            raw_posts: List of raw post objects from platform
        
        Returns:
            List of normalized post dictionaries
        """
        normalized = []
        for post in raw_posts:
            normalized_post = self.normalizer.normalize_post(post, self.platform)
            if normalized_post:
                normalized.append(normalized_post)
        
        return normalized
    
    def save_to_db(self, normalized_posts: List[Dict[str, Any]]) -> int:
        """
        Save normalized posts to database.
        
        Args:
            normalized_posts: List of normalized post dictionaries
        
        Returns:
            Number of posts successfully saved
        """
        if not normalized_posts:
            return 0
        
        # Use bulk insert for efficiency
        inserted_count = self.db_manager.bulk_insert(normalized_posts)
        logging.info(f"Saved {inserted_count}/{len(normalized_posts)} {self.platform} posts to database")
        
        return inserted_count
    
    def get_last_scrape_time(self, query: str = None) -> Optional[datetime]:
        """
        Get the timestamp of the last scrape for this platform/query.
        
        Args:
            query: Query string (optional)
        
        Returns:
            Last scrape timestamp or None
        """
        state = self.db_manager.get_scraper_state(self.platform, query)
        if state:
            return state.last_timestamp
        return None
    
    def get_last_post_id(self, query: str = None) -> Optional[str]:
        """
        Get the ID of the last scraped post for incremental scraping.
        
        Args:
            query: Query string (optional)
        
        Returns:
            Last post ID or None
        """
        state = self.db_manager.get_scraper_state(self.platform, query)
        if state:
            return state.last_post_id
        return None
    
    def update_scrape_state(self, query: str = None, last_post_id: str = None,
                           last_timestamp: datetime = None, cursor: str = None):
        """
        Update scraper state after successful scrape.
        
        Args:
            query: Query string
            last_post_id: ID of the most recent post scraped
            last_timestamp: Timestamp of the most recent post
            cursor: Pagination cursor (if applicable)
        """
        self.db_manager.update_scraper_state(
            platform=self.platform,
            query=query,
            last_post_id=last_post_id,
            last_timestamp=last_timestamp,
            cursor=cursor
        )
        logging.debug(f"Updated scraper state for {self.platform} - query: {query}")
    
    @retry_with_backoff(max_retries=SCRAPER_CONFIG['max_retries'], 
                       base_delay=SCRAPER_CONFIG['backoff_base'])
    def scrape(self, query: str = None, incremental: bool = True, 
               max_results: int = None) -> int:
        """
        Main scraping method - coordinates fetching, normalizing, and saving.
        
        Args:
            query: Search query (keywords, subreddit, etc.)
            incremental: If True, only fetch posts since last scrape
            max_results: Maximum posts to fetch (uses config default if None)
        
        Returns:
            Number of posts successfully saved
        """
        if not self.authenticated:
            if not self.authenticate():
                logging.error(f"Authentication failed for {self.platform}")
                return 0
        
        # Get last scrape state for incremental scraping
        since_id = None
        since_time = None
        
        if incremental:
            since_id = self.get_last_post_id(query)
            since_time = self.get_last_scrape_time(query)
            
            if since_id:
                logging.info(f"Incremental scrape for {self.platform} - since_id: {since_id}")
            elif since_time:
                logging.info(f"Incremental scrape for {self.platform} - since_time: {since_time}")
        
        # Fetch posts
        max_fetch = max_results or SCRAPER_CONFIG['max_posts_per_fetch']
        logging.info(f"Fetching up to {max_fetch} posts from {self.platform} - query: {query}")
        
        raw_posts = self.fetch_posts(
            query=query,
            since_id=since_id,
            since_time=since_time,
            max_results=max_fetch
        )
        
        if not raw_posts:
            logging.info(f"No new posts found on {self.platform}")
            return 0
        
        logging.info(f"Fetched {len(raw_posts)} posts from {self.platform}")
        
        # Normalize data
        normalized_posts = self.normalize_data(raw_posts)
        
        if not normalized_posts:
            logging.warning(f"No posts could be normalized from {self.platform}")
            return 0
        
        # Save to database
        saved_count = self.save_to_db(normalized_posts)
        
        # Update scraper state with the most recent post
        if normalized_posts:
            most_recent = normalized_posts[0]  # Assuming posts are in reverse chronological order
            self.update_scrape_state(
                query=query,
                last_post_id=most_recent.get('post_id'),
                last_timestamp=most_recent.get('created_at')
            )
        
        return saved_count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for this scraper.
        
        Returns:
            Dictionary with stats (post count, last scrape time, etc.)
        """
        total_posts = self.db_manager.get_post_count(self.platform)
        recent_posts = self.db_manager.get_recent_posts(self.platform, limit=5)
        
        return {
            'platform': self.platform,
            'total_posts': total_posts,
            'authenticated': self.authenticated,
            'recent_posts_count': len(recent_posts),
        }
