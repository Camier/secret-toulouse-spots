#!/usr/bin/env python3
"""
Main scraper orchestrator using unified scrapers
Coordinates all data collection from various sources
"""

import argparse
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from unified_instagram_scraper import UnifiedInstagramScraper
from unified_reddit_scraper import UnifiedRedditScraper

# Import other scrapers
try:
    from forum_scraper import ForumScraper
    HAS_FORUM = True
except ImportError:
    HAS_FORUM = False

try:
    from openstreetmap_scraper import OSMSpotScraper
    HAS_OSM = True
except ImportError:
    HAS_OSM = False

try:
    from tourism_sites_scraper import TourismScraper
    HAS_TOURISM = True
except ImportError:
    HAS_TOURISM = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class UnifiedScraperOrchestrator:
    """Orchestrates all scrapers with unified interface"""
    
    def __init__(self, db_path: str = "../hidden_spots.db"):
        self.db_path = Path(db_path)
        self.scrapers = {}
        self.stats = {
            "start_time": datetime.now(),
            "scrapers_run": 0,
            "total_spots": 0,
            "spots_by_source": {}
        }
        
        # Ensure database exists
        if not self.db_path.exists():
            logger.error(f"Database not found at {self.db_path}")
            logger.info("Run setup_database.py first")
            raise FileNotFoundError("Database not found")
            
    def add_instagram_scraper(self, mode: str = "basic", **kwargs):
        """Add Instagram scraper with specified mode"""
        scraper = UnifiedInstagramScraper(mode=mode, **kwargs)
        self.scrapers["instagram"] = scraper
        logger.info(f"Added Instagram scraper in {mode} mode")
        
    def add_reddit_scraper(self, mode: str = "basic", **kwargs):
        """Add Reddit scraper with specified mode"""
        scraper = UnifiedRedditScraper(mode=mode, **kwargs)
        self.scrapers["reddit"] = scraper
        logger.info(f"Added Reddit scraper in {mode} mode")
        
    def add_osm_scraper(self):
        """Add OpenStreetMap scraper"""
        if HAS_OSM:
            scraper = OSMSpotScraper()
            self.scrapers["osm"] = scraper
            logger.info("Added OpenStreetMap scraper")
        else:
            logger.warning("OpenStreetMap scraper not available")
            
    def add_forum_scraper(self):
        """Add forum scraper"""
        if HAS_FORUM:
            scraper = ForumScraper()
            self.scrapers["forum"] = scraper
            logger.info("Added Forum scraper")
        else:
            logger.warning("Forum scraper not available")
            
    def add_tourism_scraper(self):
        """Add tourism sites scraper"""
        if HAS_TOURISM:
            scraper = TourismScraper()
            self.scrapers["tourism"] = scraper
            logger.info("Added Tourism scraper")
        else:
            logger.warning("Tourism scraper not available")
            
    def run_all(self, **kwargs):
        """Run all configured scrapers"""
        logger.info("=" * 60)
        logger.info("🚀 STARTING UNIFIED SCRAPER ORCHESTRATOR")
        logger.info("=" * 60)
        
        for name, scraper in self.scrapers.items():
            logger.info(f"\n{'='*40}")
            logger.info(f"Running {name.upper()} scraper...")
            logger.info(f"{'='*40}")
            
            try:
                # Get scraper-specific kwargs
                scraper_kwargs = kwargs.get(name, {})
                
                # Run the scraper
                spots_saved = scraper.run(**scraper_kwargs)
                
                # Update stats
                self.stats["scrapers_run"] += 1
                self.stats["total_spots"] += spots_saved
                self.stats["spots_by_source"][name] = spots_saved
                
                logger.info(f"✅ {name} scraper completed: {spots_saved} spots saved")
                
            except Exception as e:
                logger.error(f"❌ {name} scraper failed: {e}")
                
            # Delay between scrapers
            if name != list(self.scrapers.keys())[-1]:
                time.sleep(5)
                
        self._print_summary()
        
    def _print_summary(self):
        """Print scraping summary"""
        duration = datetime.now() - self.stats["start_time"]
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 SCRAPING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Duration: {duration}")
        logger.info(f"Scrapers run: {self.stats['scrapers_run']}")
        logger.info(f"Total spots saved: {self.stats['total_spots']}")
        logger.info("\nSpots by source:")
        
        for source, count in self.stats["spots_by_source"].items():
            logger.info(f"  - {source}: {count} spots")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Unified Scraper Orchestrator")
    
    # Global options
    parser.add_argument("--sources", nargs="+", 
                        choices=["instagram", "reddit", "osm", "forum", "tourism", "all"],
                        default=["all"], help="Sources to scrape")
    parser.add_argument("--limit", type=int, default=50,
                        help="Default limit for scrapers")
    
    # Instagram options
    parser.add_argument("--instagram-mode", choices=["basic", "secure", "continuous"],
                        default="basic", help="Instagram scraping mode")
    parser.add_argument("--instagram-username", help="Instagram username")
    parser.add_argument("--instagram-password", help="Instagram password")
    parser.add_argument("--instagram-duration", type=int, default=300,
                        help="Duration for continuous mode (seconds)")
    
    # Reddit options
    parser.add_argument("--reddit-mode", choices=["basic", "praw", "mcp"],
                        default="basic", help="Reddit scraping mode")
    parser.add_argument("--reddit-client-id", help="Reddit client ID")
    parser.add_argument("--reddit-client-secret", help="Reddit client secret")
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = UnifiedScraperOrchestrator()
    
    # Configure scrapers based on sources
    sources = args.sources if "all" not in args.sources else ["instagram", "reddit", "osm", "forum", "tourism"]
    
    if "instagram" in sources:
        orchestrator.add_instagram_scraper(
            mode=args.instagram_mode,
            username=args.instagram_username,
            password=args.instagram_password,
            continuous_duration=args.instagram_duration
        )
        
    if "reddit" in sources:
        orchestrator.add_reddit_scraper(
            mode=args.reddit_mode,
            client_id=args.reddit_client_id,
            client_secret=args.reddit_client_secret
        )
        
    if "osm" in sources:
        orchestrator.add_osm_scraper()
        
    if "forum" in sources:
        orchestrator.add_forum_scraper()
        
    if "tourism" in sources:
        orchestrator.add_tourism_scraper()
        
    # Prepare kwargs for each scraper
    scraper_kwargs = {
        "instagram": {"limit": args.limit},
        "reddit": {"limit": args.limit},
        "osm": {},
        "forum": {},
        "tourism": {}
    }
    
    # Run all scrapers
    orchestrator.run_all(**scraper_kwargs)


if __name__ == "__main__":
    main()