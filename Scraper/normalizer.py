"""
Data normalizer to transform platform-specific data to unified schema.
"""
from typing import Dict, Any, List
from datetime import datetime
import logging

from utils import extract_hashtags, extract_mentions, extract_urls, parse_platform_timestamp


class DataNormalizer:
    """Normalizes social media posts from different platforms to a unified schema."""
    
    @staticmethod
    def normalize_twitter_post(tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Twitter/X post data.
        
        Args:
            tweet_data: Raw tweet data from Tweepy
        
        Returns:
            Normalized post dictionary
        """
        try:
            # Extract core data
            tweet_id = tweet_data.get('id_str') or str(tweet_data.get('id'))
            text = tweet_data.get('text') or tweet_data.get('full_text', '')
            
            # Author information
            author = tweet_data.get('user', {})
            author_id = author.get('id_str') or str(author.get('id', ''))
            author_username = author.get('screen_name', '')
            author_display_name = author.get('name', '')
            author_followers = author.get('followers_count', 0)
            
            # Engagement metrics
            public_metrics = tweet_data.get('public_metrics', {})
            like_count = public_metrics.get('like_count') or tweet_data.get('favorite_count', 0)
            reply_count = public_metrics.get('reply_count') or tweet_data.get('reply_count', 0)
            retweet_count = public_metrics.get('retweet_count') or tweet_data.get('retweet_count', 0)
            view_count = public_metrics.get('impression_count', 0)
            
            # Post properties
            is_reply = 'in_reply_to_status_id' in tweet_data or 'in_reply_to_user_id' in tweet_data
            is_repost = 'retweeted_status' in tweet_data or tweet_data.get('referenced_tweets', [{}])[0].get('type') == 'retweeted'
            has_media = 'media' in tweet_data.get('entities', {}) or 'extended_entities' in tweet_data
            
            # Timestamp
            created_at_str = tweet_data.get('created_at', '')
            created_at = parse_platform_timestamp(created_at_str, 'twitter')
            
            # Language
            language = tweet_data.get('lang', 'unknown')
            
            # Platform URL
            platform_url = f"https://twitter.com/{author_username}/status/{tweet_id}"
            
            # Extract hashtags from text
            hashtags = extract_hashtags(text)
            
            return {
                'post_id': tweet_id,
                'platform': 'twitter',
                'platform_url': platform_url,
                'text': text,
                'language': language,
                'author_id': author_id,
                'author_username': author_username,
                'author_display_name': author_display_name,
                'author_followers': author_followers,
                'like_count': like_count,
                'reply_count': reply_count,
                'retweet_count': retweet_count,
                'view_count': view_count,
                'is_reply': is_reply,
                'is_repost': is_repost,
                'has_media': has_media,
                'created_at': created_at,
                'raw_json': tweet_data,
                'hashtags': hashtags,
            }
        except Exception as e:
            logging.error(f"Error normalizing Twitter post: {e}")
            return None
    
    @staticmethod
    def normalize_reddit_post(submission_data: Any) -> Dict[str, Any]:
        """
        Normalize Reddit post data.
        
        Args:
            submission_data: PRAW Submission object
        
        Returns:
            Normalized post dictionary
        """
        try:
            # PRAW Submission object has attributes only
            post_id = submission_data.id
            
            # Combine title and selftext for full text
            title = submission_data.title
            selftext = submission_data.selftext or ''
            text = f"{title}\n\n{selftext}" if selftext else title
            
            # Author information
            author = submission_data.author
            if author:
                author_username = author.name if hasattr(author, 'name') else str(author)
                # Try to get karma if available
                try:
                    author_followers = author.link_karma + author.comment_karma
                except:
                    author_followers = 0
            else:
                author_username = '[deleted]'
                author_followers = 0
            
            # Engagement metrics
            like_count = submission_data.ups
            reply_count = submission_data.num_comments
            
            # Post properties
            is_self = submission_data.is_self
            has_media = not is_self
            
            # Timestamp
            created_utc = submission_data.created_utc
            created_at = datetime.fromtimestamp(created_utc)
            
            # Subreddit
            subreddit = submission_data.subreddit
            subreddit_name = subreddit.display_name if hasattr(subreddit, 'display_name') else str(subreddit)
            
            # Platform URL
            permalink = submission_data.permalink
            platform_url = f"https://reddit.com{permalink}"
            
            # Extract hashtags from text (though Reddit doesn't use hashtags commonly)
            hashtags = extract_hashtags(text)
            
            return {
                'post_id': post_id,
                'platform': 'reddit',
                'platform_url': platform_url,
                'text': text,
                'language': 'en',  # Reddit doesn't provide language
                'author_id': author_username,  # Reddit uses username as ID
                'author_username': author_username,
                'author_display_name': author_username,
                'author_followers': author_followers,
                'like_count': like_count,
                'reply_count': reply_count,
                'retweet_count': 0,  # Reddit doesn't have retweets
                'view_count': 0,  # Reddit doesn't provide view count publicly
                'is_reply': False,  # This is for submissions only
                'is_repost': False,
                'has_media': has_media,
                'created_at': created_at,
                'raw_json': {
                    'subreddit': subreddit_name,
                    'score': submission_data.score,
                    'url': submission_data.url,
                },
                'hashtags': hashtags,
            }
        except Exception as e:
            logging.error(f"Error normalizing Reddit post: {e}")
            return None
    
    @staticmethod
    def normalize_bluesky_post(post_data: Any) -> Dict[str, Any]:
        """
        Normalize Bluesky post data.
        
        Args:
            post_data: atproto post object
        
        Returns:
            Normalized post dictionary
        """
        try:
            # Bluesky post object has attributes
            post_uri = getattr(post_data, 'uri', '')
            # Extract the post ID from the URI (at://did:plc:xxx/app.bsky.feed.post/yyy)
            post_id = post_uri.split('/')[-1] if post_uri else ''
            
            # Validate post_id - must not be empty
            if not post_id:
                logging.warning(f"Skipping Bluesky post with empty post_id. URI: {post_uri}")
                return None
            
            # Get the record (actual post content) - this is also an object
            record = getattr(post_data, 'record', None)
            text = getattr(record, 'text', '') if record else ''
            
            # Author information - author is also an object
            author = getattr(post_data, 'author', None)
            if author:
                author_did = getattr(author, 'did', '')  # Decentralized ID
                author_username = getattr(author, 'handle', '')
                author_display_name = getattr(author, 'display_name', author_username)
                author_followers = getattr(author, 'followers_count', 0)
            else:
                author_did = ''
                author_username = ''
                author_display_name = ''
                author_followers = 0
            
            # Engagement metrics (if available in the response)
            like_count = getattr(post_data, 'like_count', 0)
            reply_count = getattr(post_data, 'reply_count', 0)
            retweet_count = getattr(post_data, 'repost_count', 0)
            
            # Post properties
            reply = getattr(record, 'reply', None) if record else None
            is_reply = bool(reply)
            
            # Check for repost reason
            reason = getattr(post_data, 'reason', None)
            is_repost = False
            if reason:
                reason_type = getattr(reason, 'py_type', '')
                is_repost = 'reasonRepost' in reason_type if reason_type else False
            
            # Check for embeds (media)
            embed = getattr(record, 'embed', None) if record else None
            has_media = False
            if embed:
                has_media = hasattr(embed, 'images') or hasattr(embed, 'external')
            
            # Timestamp
            created_at_str = getattr(record, 'created_at', '') if record else ''
            created_at = parse_platform_timestamp(created_at_str, 'bluesky')
            
            # Language
            langs = getattr(record, 'langs', []) if record else []
            language = langs[0] if langs else 'unknown'
            
            # Platform URL (construct from handle and post ID)
            platform_url = f"https://bsky.app/profile/{author_username}/post/{post_id}"
            
            # Extract hashtags from text
            hashtags = extract_hashtags(text)
            
            return {
                'post_id': post_id,
                'platform': 'bluesky',
                'platform_url': platform_url,
                'text': text,
                'language': language,
                'author_id': author_did,
                'author_username': author_username,
                'author_display_name': author_display_name,
                'author_followers': author_followers,
                'like_count': like_count,
                'reply_count': reply_count,
                'retweet_count': retweet_count,
                'view_count': 0,
                'is_reply': is_reply,
                'is_repost': is_repost,
                'has_media': has_media,
                'created_at': created_at,
                'raw_json': str(post_data),  # Convert object to string for JSON storage
                'hashtags': hashtags,
            }
        except Exception as e:
            logging.error(f"Error normalizing Bluesky post: {e}")
            return None
    
    @staticmethod
    def normalize_post(post_data: Any, platform: str) -> Dict[str, Any]:
        """
        Normalize post from any platform.
        
        Args:
            post_data: Raw post data
            platform: Platform name (twitter, reddit, bluesky, threads)
        
        Returns:
            Normalized post dictionary
        """
        if platform == 'twitter':
            return DataNormalizer.normalize_twitter_post(post_data)
        elif platform == 'reddit':
            return DataNormalizer.normalize_reddit_post(post_data)
        elif platform == 'bluesky':
            return DataNormalizer.normalize_bluesky_post(post_data)
        else:
            logging.error(f"Unknown platform: {platform}")
            return None
