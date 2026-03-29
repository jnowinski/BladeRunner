#!/usr/bin/env python3
"""
Main entry point for the social media scraper.
Provides CLI for controlling the scraper daemon.
"""
import sys
import argparse
from daemon import ScraperDaemon


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Multi-Platform Social Media Scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scraper.py start                          # Start scraping all configured platforms
  python scraper.py start --platforms twitter reddit   # Start scraping specific platforms
  python scraper.py status                         # Check daemon status
  python scraper.py stop                           # Stop the daemon
  python scraper.py restart                        # Restart the daemon
        """
    )
    
    parser.add_argument(
        'command',
        choices=['start', 'stop', 'restart', 'status'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--platforms',
        nargs='+',
        choices=['twitter', 'reddit', 'bluesky', 'threads'],
        help='Platforms to scrape (default: all configured platforms)',
        default=None
    )
    
    args = parser.parse_args()
    
    # Initialize daemon
    daemon = ScraperDaemon()
    
    # Execute command
    if args.command == 'start':
        success = daemon.start(platforms=args.platforms)
        sys.exit(0 if success else 1)
    
    elif args.command == 'stop':
        success = daemon.stop()
        sys.exit(0 if success else 1)
    
    elif args.command == 'restart':
        success = daemon.restart(platforms=args.platforms)
        sys.exit(0 if success else 1)
    
    elif args.command == 'status':
        is_running = daemon.status()
        sys.exit(0 if is_running else 1)


if __name__ == '__main__':
    main()
