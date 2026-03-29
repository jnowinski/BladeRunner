"""
Utility functions for the scraper: rate limiting, logging, signal handling, etc.
"""
import os
import re
import sys
import time
import signal
import logging
from functools import wraps
from datetime import datetime, timedelta
from typing import List, Callable
from logging.handlers import RotatingFileHandler

from config import LOGGING_CONFIG, SCRAPER_CONFIG


class RateLimiter:
    """Rate limiter with exponential backoff."""
    
    def __init__(self, max_requests: int, period: int):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests
            period: Time period in seconds
        """
        self.max_requests = max_requests
        self.period = period
        self.requests = []
    
    def wait_if_needed(self):
        """Wait if rate limit is exceeded."""
        now = time.time()
        
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.period]
        
        if len(self.requests) >= self.max_requests:
            # Calculate wait time
            oldest_request = min(self.requests)
            wait_time = self.period - (now - oldest_request)
            
            if wait_time > 0:
                logging.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
                time.sleep(wait_time + 1)  # Add 1 second buffer
        
        # Record this request
        self.requests.append(time.time())
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply rate limiting to a function."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.wait_if_needed()
            return func(*args, **kwargs)
        return wrapper


def retry_with_backoff(max_retries: int = 3, base_delay: int = 60):
    """
    Decorator to retry a function with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        logging.error(f"Max retries exceeded for {func.__name__}: {e}")
                        raise
                    
                    delay = base_delay * (2 ** (retries - 1))
                    logging.warning(f"Error in {func.__name__}: {e}. Retrying in {delay}s... (Attempt {retries}/{max_retries})")
                    time.sleep(delay)
        
        return wrapper
    return decorator


def extract_hashtags(text: str) -> List[str]:
    """
    Extract hashtags from text.
    
    Args:
        text: Text to extract hashtags from
    
    Returns:
        List of hashtags (without # symbol)
    """
    if not text:
        return []
    
    # Match hashtags (word characters after #)
    hashtags = re.findall(r'#(\w+)', text)
    return list(set(hashtags))  # Remove duplicates


def extract_mentions(text: str) -> List[str]:
    """
    Extract mentions from text.
    
    Args:
        text: Text to extract mentions from
    
    Returns:
        List of mentions (without @ symbol)
    """
    if not text:
        return []
    
    # Match mentions (word characters after @)
    mentions = re.findall(r'@(\w+)', text)
    return list(set(mentions))


def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text.
    
    Args:
        text: Text to extract URLs from
    
    Returns:
        List of URLs
    """
    if not text:
        return []
    
    # Simple URL regex (matches http/https URLs)
    urls = re.findall(r'https?://[^\s]+', text)
    return urls


def setup_logging(log_to_file: bool = True):
    """
    Set up logging configuration.
    
    Args:
        log_to_file: Whether to log to file (in addition to console)
    """
    # Create logs directory if it doesn't exist
    if log_to_file:
        os.makedirs(LOGGING_CONFIG['log_dir'], exist_ok=True)
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Set up root logger
    logger = logging.getLogger()
    logger.setLevel(LOGGING_CONFIG['log_level'])
    
    # Clear existing handlers
    logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_to_file:
        log_file = os.path.join(LOGGING_CONFIG['log_dir'], LOGGING_CONFIG['log_file'])
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=LOGGING_CONFIG['max_bytes'],
            backupCount=LOGGING_CONFIG['backup_count']
        )
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        logger.addHandler(file_handler)
    
    return logger


class PIDFileManager:
    """Manages PID file for daemon process."""
    
    def __init__(self, pid_file: str):
        """
        Initialize PID file manager.
        
        Args:
            pid_file: Path to PID file
        """
        self.pid_file = pid_file
    
    def write_pid(self):
        """Write current process PID to file."""
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
    
    def read_pid(self) -> int:
        """Read PID from file."""
        try:
            with open(self.pid_file, 'r') as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError):
            return None
    
    def remove_pid(self):
        """Remove PID file."""
        try:
            os.remove(self.pid_file)
        except FileNotFoundError:
            pass
    
    def is_running(self) -> bool:
        """Check if process with PID from file is running."""
        pid = self.read_pid()
        if pid is None:
            return False
        
        try:
            # Check if process exists (works on Unix and Windows)
            os.kill(pid, 0)
            return True
        except OSError:
            return False
        except AttributeError:
            # Windows doesn't support signal 0, use alternative
            import psutil
            return psutil.pid_exists(pid)


class SignalHandler:
    """Handles shutdown signals gracefully."""
    
    def __init__(self):
        """Initialize signal handler."""
        self.shutdown_requested = False
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        """Handle shutdown signal."""
        logging.info(f"Received signal {signum}. Initiating graceful shutdown...")
        self.shutdown_requested = True
    
    def should_shutdown(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_requested


def format_timestamp(dt: datetime) -> str:
    """Format datetime for display."""
    if dt is None:
        return "N/A"
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def calculate_engagement_rate(likes: int, replies: int, followers: int) -> float:
    """
    Calculate engagement rate.
    
    Args:
        likes: Number of likes
        replies: Number of replies
        followers: Number of followers
    
    Returns:
        Engagement rate as percentage
    """
    if followers == 0:
        return 0.0
    return ((likes + replies) / followers) * 100


def parse_platform_timestamp(timestamp_str: str, platform: str) -> datetime:
    """
    Parse timestamp string from different platforms.
    
    Args:
        timestamp_str: Timestamp string
        platform: Platform name (twitter, reddit, bluesky, threads)
    
    Returns:
        Parsed datetime object
    """
    # Handle empty or None timestamps
    if not timestamp_str:
        return datetime.utcnow()
    
    try:
        if platform == 'twitter':
            # Twitter uses ISO 8601 format
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        elif platform == 'reddit':
            # Reddit uses Unix timestamp
            return datetime.fromtimestamp(float(timestamp_str))
        elif platform == 'bluesky':
            # Bluesky uses ISO 8601 format
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            # Default: try ISO format
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except (ValueError, TypeError, AttributeError) as e:
        # If parsing fails, return current time
        logging.warning(f"Failed to parse timestamp '{timestamp_str}' for platform {platform}: {e}")
        return datetime.utcnow()
