"""
Daemon manager for running the scraper as a background service with lifecycle control.
"""
import os
import sys
import time
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from database import DatabaseManager
from scraper_manager import ScraperManager
from utils import PIDFileManager, SignalHandler, setup_logging
from config import DAEMON_CONFIG


class ScraperDaemon:
    """Manages the scraper daemon lifecycle."""
    
    def __init__(self):
        """Initialize scraper daemon."""
        self.pid_manager = PIDFileManager(DAEMON_CONFIG['pid_file'])
        self.state_file = DAEMON_CONFIG['state_file']
        self.signal_handler = None
        self.db_manager = None
        self.scraper_manager = None
        self.running = False
    
    def is_running(self) -> bool:
        """Check if daemon is already running."""
        return self.pid_manager.is_running()
    
    def get_pid(self) -> Optional[int]:
        """Get PID of running daemon."""
        return self.pid_manager.read_pid()
    
    def save_state(self):
        """Save current state to file."""
        try:
            state = {
                'last_save_time': datetime.now().isoformat(),
                'stats': self.scraper_manager.stats if self.scraper_manager else {},
                'status': 'running' if self.running else 'stopped',
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            
            logging.debug("State saved to file")
        except Exception as e:
            logging.error(f"Error saving state: {e}")
    
    def load_state(self) -> Optional[Dict[str, Any]]:
        """Load state from file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                logging.info("State loaded from file")
                return state
            return None
        except Exception as e:
            logging.error(f"Error loading state: {e}")
            return None
    
    def cleanup(self):
        """Cleanup daemon resources."""
        logging.info("Cleaning up daemon resources...")
        
        # Save state before cleanup
        if self.scraper_manager:
            self.save_state()
        
        # Stop scraping
        if self.scraper_manager:
            try:
                self.scraper_manager.stop_scheduled_scraping()
            except Exception as e:
                logging.error(f"Error stopping scraper manager: {e}")
        
        # Remove PID file
        self.pid_manager.remove_pid()
        
        logging.info("Cleanup complete")
    
    def start(self, platforms: list = None):
        """
        Start the scraper daemon.
        
        Args:
            platforms: List of platforms to scrape (None = all configured)
        """
        # Check if already running
        if self.is_running():
            existing_pid = self.get_pid()
            print(f"ERROR: Scraper daemon is already running (PID: {existing_pid})")
            logging.error(f"Daemon already running with PID {existing_pid}")
            return False
        
        # Set up logging
        setup_logging(log_to_file=True)
        
        logging.info("="*60)
        logging.info("Starting scraper daemon...")
        logging.info("="*60)
        
        # Write PID file
        self.pid_manager.write_pid()
        current_pid = os.getpid()
        logging.info(f"Daemon PID: {current_pid}")
        
        # Set up signal handler for graceful shutdown
        self.signal_handler = SignalHandler()
        
        # Initialize database manager
        try:
            self.db_manager = DatabaseManager()
            self.db_manager.create_tables()
            logging.info("Database connection established")
        except Exception as e:
            logging.error(f"Failed to initialize database: {e}")
            self.cleanup()
            return False
        
        # Initialize scraper manager
        try:
            self.scraper_manager = ScraperManager(self.db_manager)
            logging.info("Scraper manager initialized")
        except Exception as e:
            logging.error(f"Failed to initialize scraper manager: {e}")
            self.cleanup()
            return False
        
        # Load previous state if exists
        previous_state = self.load_state()
        if previous_state:
            logging.info(f"Loaded previous state from {previous_state.get('last_save_time')}")
        
        # Start scheduled scraping
        try:
            self.scraper_manager.start_scheduled_scraping(platforms)
            self.running = True
            logging.info("Scraper daemon started successfully")
            print(f"✓ Scraper daemon started (PID: {current_pid})")
            print(f"  Logs: {os.path.join('logs', 'scraper.log')}")
            print(f"  Use 'python scraper.py status' to check status")
            print(f"  Use 'python scraper.py stop' to stop the daemon")
        except Exception as e:
            logging.error(f"Failed to start scheduled scraping: {e}")
            self.cleanup()
            return False
        
        # Main daemon loop
        try:
            logging.info("Entering main daemon loop...")
            save_interval = 300  # Save state every 5 minutes
            last_save = time.time()
            
            while not self.signal_handler.should_shutdown():
                time.sleep(1)
                
                # Periodically save state
                if time.time() - last_save > save_interval:
                    self.save_state()
                    last_save = time.time()
            
            logging.info("Shutdown signal received")
            
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt received")
        except Exception as e:
            logging.error(f"Unexpected error in daemon loop: {e}")
        finally:
            self.running = False
            self.cleanup()
            logging.info("Daemon stopped")
            print("✓ Scraper daemon stopped")
        
        return True
    
    def stop(self):
        """Stop the running daemon."""
        if not self.is_running():
            print("ERROR: Scraper daemon is not running")
            logging.warning("Attempted to stop daemon but it's not running")
            return False
        
        pid = self.get_pid()
        
        try:
            # Send SIGTERM to gracefully shutdown
            logging.info(f"Sending SIGTERM to PID {pid}")
            print(f"Stopping scraper daemon (PID: {pid})...")
            
            os.kill(pid, 15)  # SIGTERM
            
            # Wait for process to stop (with timeout)
            timeout = 30
            start_time = time.time()
            
            while self.is_running() and (time.time() - start_time) < timeout:
                time.sleep(1)
                print(".", end="", flush=True)
            
            print()  # Newline after dots
            
            if self.is_running():
                print("WARNING: Daemon did not stop gracefully, force killing...")
                logging.warning("Daemon did not stop gracefully, sending SIGKILL")
                os.kill(pid, 9)  # SIGKILL
                time.sleep(2)
            
            if not self.is_running():
                print("✓ Scraper daemon stopped successfully")
                logging.info("Daemon stopped successfully")
                return True
            else:
                print("ERROR: Failed to stop daemon")
                logging.error("Failed to stop daemon")
                return False
                
        except ProcessLookupError:
            # Process doesn't exist, cleanup PID file
            print("WARNING: Process not found, cleaning up PID file")
            logging.warning("Process not found, cleaning up stale PID file")
            self.pid_manager.remove_pid()
            return True
        except Exception as e:
            print(f"ERROR: Failed to stop daemon: {e}")
            logging.error(f"Error stopping daemon: {e}")
            return False
    
    def status(self):
        """Get and display daemon status."""
        is_running = self.is_running()
        pid = self.get_pid()
        
        print("="*60)
        print("SCRAPER DAEMON STATUS")
        print("="*60)
        
        if is_running:
            print(f"Status:       RUNNING")
            print(f"PID:          {pid}")
            
            # Load state file to show more details
            state = self.load_state()
            if state:
                print(f"Last Updated: {state.get('last_save_time', 'N/A')}")
                
                stats = state.get('stats', {})
                if stats:
                    print(f"\nStatistics:")
                    print(f"  Total Scrapes:      {stats.get('total_scrapes', 0)}")
                    print(f"  Successful Scrapes: {stats.get('successful_scrapes', 0)}")
                    print(f"  Failed Scrapes:     {stats.get('failed_scrapes', 0)}")
                    print(f"  Total Posts:        {stats.get('total_posts_collected', 0)}")
                    
                    if stats.get('start_time'):
                        start_time = datetime.fromisoformat(stats['start_time'])
                        uptime = datetime.now() - start_time
                        print(f"  Uptime:             {str(uptime).split('.')[0]}")
            
            print(f"\nLog File:     {os.path.join('logs', 'scraper.log')}")
            print(f"State File:   {self.state_file}")
            
        else:
            print(f"Status:       STOPPED")
            if os.path.exists(self.state_file):
                state = self.load_state()
                if state:
                    print(f"Last Run:     {state.get('last_save_time', 'N/A')}")
        
        print("="*60)
        
        return is_running
    
    def restart(self, platforms: list = None):
        """Restart the daemon."""
        print("Restarting scraper daemon...")
        
        if self.is_running():
            if not self.stop():
                print("ERROR: Failed to stop daemon")
                return False
            
            # Wait a moment before restarting
            time.sleep(2)
        
        return self.start(platforms)
