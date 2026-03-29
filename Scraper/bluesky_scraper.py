"""
Bluesky scraper using atproto library.
"""
import logging
from typing import List, Any, Optional
from datetime import datetime

from atproto import Client

from base_scraper import BaseScraper
from database import DatabaseManager
from utils import RateLimiter
from config import BLUESKY_CONFIG, SCRAPER_CONFIG


class BlueskyScraper(BaseScraper):
    """Scraper for Bluesky using the AT Protocol."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize Bluesky scraper."""
        super().__init__('bluesky', db_manager)
        self.client = None
        self.rate_limiter = RateLimiter(
            max_requests=self.max_requests,
            period=self.period
        )
    
    def authenticate(self) -> bool:
        """
        Authenticate with Bluesky using handle and app password.
        
        Returns:
            True if authentication successful
        """
        try:
            handle = BLUESKY_CONFIG['handle']
            app_password = BLUESKY_CONFIG['app_password']
            
            if not all([handle, app_password]):
                logging.error("Bluesky credentials not configured")
                return False
            
            # Initialize atproto client
            self.client = Client()
            
            # Login with handle and app password
            self.client.login(handle, app_password)
            
            self.authenticated = True
            logging.info(f"Bluesky authentication successful for {handle}")
            return True
            
        except Exception as e:
            logging.error(f"Bluesky authentication failed: {e}")
            self.authenticated = False
            return False
    
    def fetch_posts(self, query: str = None, since_id: str = None,
                   since_time: datetime = None, max_results: int = 100) -> List[Any]:
        """
        Fetch posts from Bluesky.
        
        Args:
            query: Search query string
            since_id: Not widely used in Bluesky (uses cursor/timestamp)
            since_time: Fetch posts after this timestamp
            max_results: Maximum number of posts to fetch
        
        Returns:
            List of post objects
        """
        if not self.authenticated:
            logging.error("Not authenticated with Bluesky")
            return []
        
        try:
            # Apply rate limiting
            self.rate_limiter.wait_if_needed()
            
            posts = []
            
            if query:
                # Search for posts using the query
                logging.info(f"Searching Bluesky for: {query}")
                
                try:
                    # Use search_posts method
                    response = self.client.app.bsky.feed.search_posts({
                        'q': query,
                        'limit': min(max_results, 100)  # API limit
                    })
                    
                    if response and hasattr(response, 'posts'):
                        posts = response.posts
                    
                except AttributeError:
                    # Fallback: If search_posts not available, try alternative methods
                    logging.warning("search_posts not available, using alternative method")
                    
                    # Alternative: Get timeline/feed
                    response = self.client.app.bsky.feed.get_timeline({
                        'limit': min(max_results, 100)
                    })
                    
                    if response and hasattr(response, 'feed'):
                        posts = [item.post for item in response.feed if hasattr(item, 'post')]
            else:
                # Get user's timeline if no query
                logging.info("Fetching Bluesky timeline")
                response = self.client.app.bsky.feed.get_timeline({
                    'limit': min(max_results, 100)
                })
                
                if response and hasattr(response, 'feed'):
                    posts = [item.post for item in response.feed if hasattr(item, 'post')]
            
            # Filter by timestamp if provided
            if since_time and posts:
                since_iso = since_time.isoformat()
                filtered_posts = []
                for p in posts:
                    if hasattr(p, 'record') and hasattr(p.record, 'created_at'):
                        created_at = getattr(p.record, 'created_at', '')
                        if created_at > since_iso:
                            filtered_posts.append(p)
                    else:
                        filtered_posts.append(p)  # Include if no timestamp
                posts = filtered_posts
            
            # Return raw atproto objects (not dicts) so normalizer can use getattr()
            logging.info(f"Fetched {len(posts)} Bluesky posts")
            return posts
            
        except Exception as e:
            logging.error(f"Error fetching Bluesky posts: {e}")
            return []
    
    def get_author_feed(self, actor: str, max_results: int = 50) -> List[Any]:
        """
        Fetch posts from a specific author's feed.
        
        Args:
            actor: Handle or DID of the author
            max_results: Maximum number of posts to fetch
        
        Returns:
            List of post objects
        """
        if not self.authenticated:
            logging.error("Not authenticated with Bluesky")
            return []
        
        try:
            self.rate_limiter.wait_if_needed()
            
            response = self.client.app.bsky.feed.get_author_feed({
                'actor': actor,
                'limit': min(max_results, 100)
            })
            
            if response and hasattr(response, 'feed'):
                posts = [item.post for item in response.feed if hasattr(item, 'post')]
                logging.info(f"Fetched {len(posts)} posts from {actor}")
                return posts
            
            return []
            
        except Exception as e:
            logging.error(f"Error fetching author feed from Bluesky: {e}")
            return []
