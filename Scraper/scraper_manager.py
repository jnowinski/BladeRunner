"""
Scraper manager that coordinates multiple platform scrapers with scheduling.
"""
import logging
from typing import Dict, List, Any
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import DatabaseManager
from twitter_scraper import TwitterScraper
from reddit_scraper import RedditScraper
from bluesky_scraper import BlueskyScraper
from threads_scraper import ThreadsScraper
from config import SCRAPER_CONFIG


class ScraperManager:
    """Manages and schedules multiple platform scrapers."""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize scraper manager.
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
        self.scheduler = BackgroundScheduler()
        
        # Initialize scrapers
        self.scrapers = {
            'twitter': TwitterScraper(db_manager),
            'reddit': RedditScraper(db_manager),
            'bluesky': BlueskyScraper(db_manager),
            'threads': ThreadsScraper(db_manager),
        }
        
        # Track statistics
        self.stats = {
            'start_time': None,
            'total_scrapes': 0,
            'successful_scrapes': 0,
            'failed_scrapes': 0,
            'total_posts_collected': 0,
        }
        
        logging.info("ScraperManager initialized")
    
    def authenticate_all(self, platforms: List[str] = None) -> Dict[str, bool]:
        """
        Authenticate all specified scrapers.
        
        Args:
            platforms: List of platform names (if None, authenticate all)
        
        Returns:
            Dictionary mapping platform to authentication status
        """
        if platforms is None:
            platforms = list(self.scrapers.keys())
        
        auth_status = {}
        for platform in platforms:
            if platform in self.scrapers:
                try:
                    auth_status[platform] = self.scrapers[platform].authenticate()
                    if auth_status[platform]:
                        logging.info(f"[OK] {platform.capitalize()} authenticated")
                    else:
                        logging.warning(f"[X] {platform.capitalize()} authentication failed")
                except Exception as e:
                    logging.error(f"[X] {platform.capitalize()} authentication error: {e}")
                    auth_status[platform] = False
        
        return auth_status
    
    def scrape_platform(self, platform: str, query: str = None, 
                       incremental: bool = True) -> int:
        """
        Scrape a single platform.
        
        Args:
            platform: Platform name
            query: Search query
            incremental: Use incremental scraping
        
        Returns:
            Number of posts collected
        """
        if platform not in self.scrapers:
            logging.error(f"Unknown platform: {platform}")
            return 0
        
        scraper = self.scrapers[platform]
        
        try:
            self.stats['total_scrapes'] += 1
            
            logging.info(f"Starting {platform} scrape - query: {query}")
            posts_count = scraper.scrape(query=query, incremental=incremental)
            
            self.stats['successful_scrapes'] += 1
            self.stats['total_posts_collected'] += posts_count
            
            logging.info(f"[OK] {platform} scrape completed - {posts_count} posts collected")
            return posts_count
            
        except Exception as e:
            self.stats['failed_scrapes'] += 1
            logging.error(f"[X] {platform} scrape failed: {e}")
            return 0
    
    def scrape_all(self, platforms: List[str] = None, incremental: bool = True) -> Dict[str, int]:
        """
        Scrape all configured platforms with their queries.
        
        Args:
            platforms: List of platforms to scrape (if None, scrape all configured)
            incremental: Use incremental scraping
        
        Returns:
            Dictionary mapping platform to number of posts collected
        """
        results = {}
        search_queries = SCRAPER_CONFIG['search_queries']
        
        if platforms is None:
            platforms = list(search_queries.keys())
        
        for platform in platforms:
            if platform not in self.scrapers:
                logging.warning(f"Platform {platform} not implemented, skipping")
                continue
            
            queries = search_queries.get(platform, [])
            
            if not queries:
                logging.warning(f"No queries configured for {platform}, skipping")
                continue
            
            platform_total = 0
            
            for query in queries:
                posts_count = self.scrape_platform(platform, query, incremental)
                platform_total += posts_count
            
            results[platform] = platform_total
        
        return results
    
    def schedule_scraping(self, platforms: List[str] = None):
        """
        Schedule periodic scraping for specified platforms.
        
        Args:
            platforms: List of platforms to schedule (if None, schedule all configured)
        """
        poll_intervals = SCRAPER_CONFIG['poll_intervals']
        search_queries = SCRAPER_CONFIG['search_queries']
        
        if platforms is None:
            platforms = list(poll_intervals.keys())
        
        for platform in platforms:
            if platform not in self.scrapers:
                logging.warning(f"Platform {platform} not implemented, skipping scheduling")
                continue
            
            interval_minutes = poll_intervals.get(platform, 15)
            queries = search_queries.get(platform, [])
            
            if not queries:
                logging.warning(f"No queries configured for {platform}, skipping scheduling")
                continue
            
            # Schedule a job for each query
            for query in queries:
                job_id = f"{platform}_{query}"
                
                self.scheduler.add_job(
                    func=self.scrape_platform,
                    trigger=IntervalTrigger(minutes=interval_minutes),
                    args=[platform, query, True],  # incremental=True
                    id=job_id,
                    name=f"Scrape {platform}: {query}",
                    replace_existing=True,
                    max_instances=1,  # Prevent overlapping runs
                )
                
                logging.info(f"Scheduled {platform} scraping every {interval_minutes} min - query: {query}")
    
    def start_scheduled_scraping(self, platforms: List[str] = None):
        """
        Start the scheduler for continuous scraping.
        
        Args:
            platforms: List of platforms to scrape
        """
        self.stats['start_time'] = datetime.now()
        
        # Authenticate before starting
        logging.info("Authenticating platforms...")
        auth_status = self.authenticate_all(platforms)
        
        # Only schedule platforms that authenticated successfully
        authenticated_platforms = [p for p, status in auth_status.items() if status]
        
        if not authenticated_platforms:
            logging.error("No platforms authenticated successfully. Cannot start scraping.")
            return
        
        # Schedule scraping jobs
        self.schedule_scraping(authenticated_platforms)
        
        # Start the scheduler
        self.scheduler.start()
        logging.info("Scheduled scraping started")
        
        # Run an initial scrape immediately
        logging.info("Running initial scrape...")
        self.scrape_all(authenticated_platforms, incremental=True)
    
    def stop_scheduled_scraping(self):
        """Stop the scheduler and all scraping jobs."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logging.info("Scheduled scraping stopped")
        else:
            logging.info("Scheduler was not running")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the scraper manager.
        
        Returns:
            Dictionary with status information
        """
        status = {
            'scheduler_running': self.scheduler.running if self.scheduler else False,
            'stats': self.stats.copy(),
            'platforms': {},
        }
        
        # Add uptime if running
        if self.stats['start_time']:
            uptime = datetime.now() - self.stats['start_time']
            status['uptime_seconds'] = uptime.total_seconds()
            status['uptime_str'] = str(uptime).split('.')[0]  # Remove microseconds
        
        # Get stats for each platform
        for platform, scraper in self.scrapers.items():
            try:
                platform_stats = scraper.get_stats()
                status['platforms'][platform] = platform_stats
            except Exception as e:
                status['platforms'][platform] = {
                    'error': str(e),
                    'authenticated': False,
                }
        
        # Get scheduled jobs info
        if self.scheduler.running:
            jobs = self.scheduler.get_jobs()
            status['scheduled_jobs'] = [
                {
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                }
                for job in jobs
            ]
        
        return status
    
    def pause_scraping(self):
        """Pause all scheduled scraping jobs."""
        if self.scheduler.running:
            self.scheduler.pause()
            logging.info("Scraping paused")
    
    def resume_scraping(self):
        """Resume all scheduled scraping jobs."""
        if self.scheduler.running:
            self.scheduler.resume()
            logging.info("Scraping resumed")
