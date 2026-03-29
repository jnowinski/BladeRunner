"""
Twitter/X scraper using Tweepy library.
"""
import logging
from typing import List, Any, Optional
from datetime import datetime

import tweepy

from base_scraper import BaseScraper
from database import DatabaseManager
from utils import RateLimiter
from config import TWITTER_CONFIG, SCRAPER_CONFIG


class TwitterScraper(BaseScraper):
    """Scraper for Twitter/X using the official API via Tweepy."""
    
    def __init__(self, db_manager: DatabaseManager):
        """Initialize Twitter scraper."""
        super().__init__('twitter', db_manager)
        self.client = None
        self.rate_limiter = RateLimiter(
            max_requests=self.max_requests,
            period=self.period
        )
    
    def authenticate(self) -> bool:
        """
        Authenticate with Twitter API using Bearer Token.
        
        Returns:
            True if authentication successful
        """
        try:
            bearer_token = TWITTER_CONFIG['bearer_token']
            
            if not bearer_token:
                logging.error("Twitter Bearer Token not configured")
                return False
            
            # Initialize Tweepy client with Bearer Token (App-only authentication)
            self.client = tweepy.Client(bearer_token=bearer_token)
            
            # Test authentication by making a simple request
            self.client.get_me()
            
            self.authenticated = True
            logging.info("Twitter authentication successful")
            return True
            
        except tweepy.TweepyException as e:
            logging.error(f"Twitter authentication failed: {e}")
            self.authenticated = False
            return False
        except Exception as e:
            logging.error(f"Unexpected error during Twitter authentication: {e}")
            self.authenticated = False
            return False
    
    def fetch_posts(self, query: str = None, since_id: str = None,
                   since_time: datetime = None, max_results: int = 100) -> List[Any]:
        """
        Fetch tweets from Twitter API.
        
        Args:
            query: Search query string
            since_id: Fetch tweets after this ID
            since_time: Fetch tweets after this timestamp
            max_results: Maximum number of tweets to fetch
        
        Returns:
            List of tweet objects
        """
        if not self.authenticated:
            logging.error("Not authenticated with Twitter")
            return []
        
        try:
            # Apply rate limiting
            self.rate_limiter.wait_if_needed()
            
            # Build query parameters
            tweet_fields = [
                'id', 'text', 'author_id', 'created_at', 'lang',
                'public_metrics', 'referenced_tweets', 'entities',
                'in_reply_to_user_id', 'possibly_sensitive'
            ]
            
            user_fields = ['id', 'name', 'username', 'public_metrics']
            expansions = ['author_id']
            
            # Limit max_results to API maximum (100 for search_recent_tweets)
            max_results = min(max_results, 100)
            
            # Search recent tweets (last 7 days for free tier)
            if query:
                response = self.client.search_recent_tweets(
                    query=query,
                    max_results=max_results,
                    since_id=since_id,
                    tweet_fields=tweet_fields,
                    user_fields=user_fields,
                    expansions=expansions
                )
            else:
                # If no query, can't fetch tweets (would need timeline, which requires user auth)
                logging.warning("No query provided for Twitter scraper")
                return []
            
            if not response.data:
                logging.info(f"No tweets found for query: {query}")
                return []
            
            # Convert to list of dicts for normalization
            tweets = []
            
            # Create a mapping of user IDs to user objects
            users = {}
            if response.includes and 'users' in response.includes:
                for user in response.includes['users']:
                    users[user.id] = user
            
            for tweet in response.data:
                # Convert tweet object to dict
                tweet_dict = {
                    'id': tweet.id,
                    'id_str': str(tweet.id),
                    'text': tweet.text,
                    'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                    'lang': tweet.lang,
                    'public_metrics': tweet.public_metrics if hasattr(tweet, 'public_metrics') else {},
                    'referenced_tweets': tweet.referenced_tweets if hasattr(tweet, 'referenced_tweets') else [],
                    'entities': tweet.entities if hasattr(tweet, 'entities') else {},
                    'in_reply_to_user_id': tweet.in_reply_to_user_id if hasattr(tweet, 'in_reply_to_user_id') else None,
                }
                
                # Add user information
                if tweet.author_id in users:
                    user = users[tweet.author_id]
                    tweet_dict['user'] = {
                        'id': user.id,
                        'id_str': str(user.id),
                        'screen_name': user.username,
                        'name': user.name,
                        'followers_count': user.public_metrics.get('followers_count', 0) if hasattr(user, 'public_metrics') else 0,
                    }
                
                tweets.append(tweet_dict)
            
            logging.info(f"Fetched {len(tweets)} tweets")
            return tweets
            
        except tweepy.TooManyRequests as e:
            logging.warning(f"Twitter rate limit exceeded: {e}")
            raise  # Let retry_with_backoff handle this
        except tweepy.TweepyException as e:
            logging.error(f"Twitter API error: {e}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error fetching tweets: {e}")
            return []
