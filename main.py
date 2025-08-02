#!/usr/bin/env python3
"""
Main entry point for Secret Toulouse Spots scraper with configuration support
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import get_config, load_env_config
from config.logging_config import setup_logging, get_scraper_logger, log_performance
from config.monitoring import get_metrics_collector, get_alert_manager, log_memory_usage

# Import scrapers
from scrapers.unified_reddit_scraper import UnifiedRedditScraper
from scrapers.unified_instagram_scraper import UnifiedInstagramScraper
from scrapers.async_reddit_scraper import AsyncRedditScraper


def setup_environment():
    """Setup environment and configuration"""
    # Load environment-specific config
    load_env_config()
    
    # Get configuration
    config = get_config()
    settings = config.config
    
    # Setup logging
    logger = setup_logging(
        level=settings.logging.level,
        log_dir=settings.logging.log_dir,
        console=settings.logging.console,
        file=settings.logging.file,
        structured=settings.logging.structured
    )
    
    return config, logger


def run_sync_scrapers(scrapers_to_run: list, config):
    """Run synchronous scrapers"""
    logger = setup_logging()
    metrics_collector = get_metrics_collector()
    alert_manager = get_alert_manager()
    
    for scraper_name in scrapers_to_run:
        try:
            # Get scraper config
            scraper_config = config.get_scraper_config(scraper_name)
            if not scraper_config:
                logger.warning(f"No configuration found for {scraper_name}")
                continue
                
            # Create logger for scraper
            scraper_logger = get_scraper_logger(scraper_name)
            
            # Start metrics tracking
            metrics = metrics_collector.start_scraper(scraper_name)
            
            # Run scraper with performance tracking
            with log_performance(logger, f"Scraper {scraper_name}"):
                if scraper_name == "reddit":
                    scraper = UnifiedRedditScraper()
                elif scraper_name == "instagram":
                    scraper = UnifiedInstagramScraper()
                elif scraper_name == "osm":
                    # OSM scraper not yet unified
                    logger.warning("OSM scraper not available in unified version")
                    continue
                else:
                    logger.error(f"Unknown scraper: {scraper_name}")
                    continue
                    
                # Run scraper
                scraper_logger.info(f"Starting {scraper_name} scraper")
                saved_count = scraper.run()
                
                # Update metrics
                metrics.spots_saved = saved_count
                log_memory_usage(metrics)
                
            # End metrics tracking
            metrics_collector.end_scraper(scraper_name)
            
            # Check for alerts
            alert_manager.check_metrics_alerts(metrics)
            
        except Exception as e:
            logger.error(f"Error running {scraper_name}: {e}", exc_info=True)
            if scraper_name in metrics_collector.metrics:
                metrics_collector.metrics[scraper_name].errors += 1


async def run_async_scrapers(scrapers_to_run: list, config):
    """Run asynchronous scrapers"""
    logger = setup_logging()
    metrics_collector = get_metrics_collector()
    
    tasks = []
    for scraper_name in scrapers_to_run:
        if scraper_name == "reddit_async":
            # Start metrics
            metrics = metrics_collector.start_scraper("reddit_async")
            
            # Create and run scraper
            scraper = AsyncRedditScraper()
            task = scraper.run()
            tasks.append(task)
    
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Async scraper failed: {result}")
            else:
                logger.info(f"Async scraper completed: {result} spots saved")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Secret Toulouse Spots Scraper")
    parser.add_argument(
        "scrapers",
        nargs="*",
        choices=["reddit", "instagram", "osm", "reddit_async", "all"],
        default=["reddit"],
        help="Scrapers to run (default: reddit)"
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Configuration file path"
    )
    parser.add_argument(
        "--env",
        choices=["development", "production", "testing"],
        help="Environment to use"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without saving to database"
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Save metrics after run"
    )
    
    args = parser.parse_args()
    
    # Set environment if specified
    if args.env:
        import os
        os.environ["SPOTS_ENV"] = args.env
    
    # Setup environment
    config, logger = setup_environment()
    
    # Apply command line overrides
    if args.debug:
        config.set("debug", True)
        config.set("logging.level", "DEBUG")
    
    # Determine scrapers to run
    scrapers = args.scrapers
    if "all" in scrapers:
        scrapers = ["reddit", "instagram", "osm"]
    
    # Separate sync and async scrapers
    sync_scrapers = [s for s in scrapers if not s.endswith("_async")]
    async_scrapers = [s for s in scrapers if s.endswith("_async")]
    
    logger.info(f"Starting scrapers: {scrapers}")
    logger.info(f"Environment: {config.get('debug') and 'debug' or 'normal'}")
    
    try:
        # Run sync scrapers
        if sync_scrapers:
            run_sync_scrapers(sync_scrapers, config)
        
        # Run async scrapers
        if async_scrapers:
            asyncio.run(run_async_scrapers(async_scrapers, config))
        
        # Save metrics if requested
        if args.metrics:
            metrics_collector = get_metrics_collector()
            metrics_collector.save_metrics()
            logger.info("Metrics saved to logs/metrics.json")
            
        # Print summary
        logger.info("=" * 60)
        logger.info("Scraping complete!")
        
        # Print metrics summary
        for name, metrics in metrics_collector.metrics.items():
            logger.info(f"{name}: {metrics.spots_saved} spots saved")
            
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()