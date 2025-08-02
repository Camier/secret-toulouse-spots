#!/usr/bin/env python3
"""
Enhanced base scraper with integrated logging and monitoring
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pathlib import Path

from config.logging_config import get_scraper_logger, log_performance
from config.monitoring import get_metrics_collector, track_operation
from config.settings import get_settings

from scrapers.base_scraper import EnhancedBaseScraper


class LoggingBaseScraper(EnhancedBaseScraper, ABC):
    """Base scraper with integrated logging and monitoring"""
    
    def __init__(self, source_name: str, db_path: str = None):
        # Get settings
        settings = get_settings()
        
        # Use configured db path if not specified
        if db_path is None:
            db_path = settings.database.path
            
        super().__init__(source_name, db_path)
        
        # Setup logging
        self.logger = get_scraper_logger(source_name)
        
        # Get metrics collector
        self.metrics_collector = get_metrics_collector()
        self.metrics = None
        
        # Apply configuration
        scraper_config = getattr(settings, source_name, None)
        if scraper_config:
            self._apply_config(scraper_config)
    
    def _apply_config(self, config):
        """Apply configuration to scraper"""
        # Update rate limiter
        if hasattr(self, 'rate_limiter'):
            self.rate_limiter.min_delay = config.min_delay
            self.rate_limiter.max_delay = config.max_delay
            self.rate_limiter.max_retries = config.max_retries
            self.rate_limiter.backoff_factor = config.backoff_factor
        
        # Update other settings
        if hasattr(config, 'user_agent_rotation_rate'):
            self.user_agent_rotation_rate = config.user_agent_rotation_rate
    
    def fetch_page(self, url: str, **kwargs) -> Optional[str]:
        """Fetch page with logging and metrics"""
        self.logger.debug(f"Fetching URL: {url}")
        
        if self.metrics:
            self.metrics.urls_fetched += 1
        
        try:
            with track_operation("fetch", self.metrics) if self.metrics else nullcontext():
                content = super().fetch_page(url, **kwargs)
                
            if content:
                self.logger.debug(f"Successfully fetched {len(content)} bytes from {url}")
            else:
                self.logger.warning(f"Failed to fetch {url}")
                if self.metrics:
                    self.metrics.errors += 1
                    
            return content
            
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}", extra={"url": url, "error_type": type(e).__name__})
            if self.metrics:
                self.metrics.errors += 1
            raise
    
    def save_spot(self, spot_data: Dict) -> bool:
        """Save spot with logging and metrics"""
        self.logger.debug(f"Saving spot: {spot_data.get('extracted_name', 'Unknown')}")
        
        try:
            with track_operation("save", self.metrics) if self.metrics else nullcontext():
                result = super().save_spot(spot_data)
                
            if result:
                self.logger.info(
                    f"Saved spot: {spot_data.get('extracted_name', 'Unknown')}",
                    extra={
                        "spot_name": spot_data.get('extracted_name'),
                        "has_coordinates": bool(spot_data.get('latitude')),
                        "is_hidden": spot_data.get('is_hidden', 0)
                    }
                )
                
                if self.metrics:
                    self.metrics.spots_saved += 1
                    if spot_data.get('latitude'):
                        self.metrics.spots_with_coordinates += 1
                    if spot_data.get('is_hidden'):
                        self.metrics.spots_hidden += 1
            else:
                self.logger.warning(f"Failed to save spot: {spot_data.get('extracted_name', 'Unknown')}")
                if self.metrics:
                    self.metrics.validation_failures += 1
                    
            return result
            
        except Exception as e:
            self.logger.error(
                f"Error saving spot: {e}",
                extra={"spot_data": spot_data, "error_type": type(e).__name__}
            )
            if self.metrics:
                self.metrics.errors += 1
            return False
    
    def run(self, **kwargs) -> int:
        """Run scraper with full logging and monitoring"""
        self.logger.info(f"Starting {self.source_name} scraper")
        
        # Start metrics tracking
        self.metrics = self.metrics_collector.start_scraper(self.source_name)
        
        try:
            # Run scraping
            spots = self.scrape(**kwargs)
            
            if self.metrics:
                self.metrics.spots_found = len(spots)
            
            self.logger.info(f"Found {len(spots)} potential spots")
            
            # Save spots
            saved_count = 0
            for spot in spots:
                if self.save_spot(spot):
                    saved_count += 1
            
            self.logger.info(
                f"Scraping complete: {saved_count}/{len(spots)} spots saved",
                extra={
                    "total_spots": len(spots),
                    "saved_spots": saved_count,
                    "success_rate": (saved_count / len(spots) * 100) if spots else 0
                }
            )
            
            return saved_count
            
        except Exception as e:
            self.logger.error(f"Scraper failed: {e}", exc_info=True)
            if self.metrics:
                self.metrics.errors += 1
            raise
            
        finally:
            # End metrics tracking
            self.metrics_collector.end_scraper(self.source_name)
            
            # Log final stats
            if self.metrics:
                self.logger.info(
                    "Scraper statistics",
                    extra={"metrics": self.metrics.to_dict()}
                )
    
    def handle_rate_limit(self):
        """Handle rate limiting with logging"""
        self.logger.warning("Rate limited, backing off")
        if self.metrics:
            self.metrics.rate_limits += 1
        super().handle_rate_limit()
    
    def _rotate_user_agent(self):
        """Rotate user agent with logging"""
        old_agent = self.current_user_agent
        super()._rotate_user_agent()
        self.logger.debug(f"Rotated user agent from {old_agent[:30]}... to {self.current_user_agent[:30]}...")


# Context manager for when metrics is None
from contextlib import contextmanager

@contextmanager
def nullcontext():
    """Null context manager for when metrics tracking is disabled"""
    yield