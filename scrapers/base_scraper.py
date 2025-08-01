#!/usr/bin/env python3
"""
Base scraper class for all data sources
Provides common functionality for rate limiting, logging, and database operations
"""

import json
import logging
import sqlite3
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import our enhanced modules
try:
    from enhanced_coordinate_extractor import EnhancedCoordinateExtractor
    from spot_data_validator import SpotDataValidator
    HAS_ENHANCED_MODULES = True
except ImportError:
    HAS_ENHANCED_MODULES = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class BaseScraper(ABC):
    """Base class for all scrapers with common functionality"""
    
    def __init__(self, source_name: str, db_path: str = "../hidden_spots.db"):
        self.source_name = source_name
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.rate_limit_delay = (1, 3)  # Min/max seconds between requests
        
        # Setup requests session with retry logic
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SecretSpotsScraper/1.0 (Educational Research)'
        })
        
        # Add retry logic
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Initialize enhanced modules if available
        if HAS_ENHANCED_MODULES:
            self.coord_extractor = EnhancedCoordinateExtractor()
            self.validator = SpotDataValidator()
        else:
            self.coord_extractor = None
            self.validator = None
        
    def get_db_connection(self) -> sqlite3.Connection:
        """Get database connection with proper path handling"""
        db_file = self.db_path if self.db_path.is_absolute() else Path(__file__).parent / self.db_path
        return sqlite3.connect(str(db_file))
        
    def rate_limit(self):
        """Apply rate limiting between requests"""
        delay = self._get_random_delay()
        time.sleep(delay)
        
    def _get_random_delay(self) -> float:
        """Get random delay between min and max"""
        import random
        return random.uniform(*self.rate_limit_delay)
        
    def save_spot(self, spot_data: Dict) -> bool:
        """Save a single spot to database with validation"""
        try:
            # Validate data if validator available
            if self.validator:
                try:
                    spot_data = self.validator.validate(spot_data)
                except Exception as e:
                    self.logger.error(f"Validation failed: {e}")
                    return False
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Ensure required fields
            spot_data.setdefault("source", self.source_name)
            spot_data.setdefault("scraped_at", datetime.now().isoformat())
            
            cursor.execute("""
                INSERT INTO spots (
                    source, source_url, raw_text, extracted_name,
                    latitude, longitude, location_type, activities,
                    is_hidden, scraped_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                spot_data.get("source"),
                spot_data.get("source_url"),
                spot_data.get("raw_text"),
                spot_data.get("extracted_name"),
                spot_data.get("latitude"),
                spot_data.get("longitude"),
                spot_data.get("location_type"),
                spot_data.get("activities"),
                spot_data.get("is_hidden", 0),
                spot_data.get("scraped_at"),
                json.dumps(spot_data.get("metadata", {}))
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving spot: {e}")
            return False
            
    def save_spots_batch(self, spots: List[Dict]) -> int:
        """Save multiple spots in a batch"""
        saved = 0
        for spot in spots:
            if self.save_spot(spot):
                saved += 1
        return saved
        
    def extract_coordinates(self, text: str) -> Optional[Tuple[float, float]]:
        """Extract coordinates from text using enhanced patterns"""
        # Use enhanced extractor if available
        if self.coord_extractor:
            return self.coord_extractor.extract_from_text(text)
        
        # Fallback to basic extraction
        import re
        
        # Pattern for decimal coordinates (now includes negative numbers)
        coord_pattern = r"(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)"
        match = re.search(coord_pattern, text)
        
        if match:
            lat, lon = float(match.group(1)), float(match.group(2))
            # Validate Toulouse region coordinates
            if 42.5 <= lat <= 44.5 and -1.0 <= lon <= 3.0:
                return lat, lon
        return None
        
    def is_secret_spot(self, text: str) -> bool:
        """Check if text indicates a secret/hidden spot"""
        keywords = [
            "secret", "caché", "cachée", "hidden", "peu connu",
            "méconnu", "confidentiel", "discret", "insolite",
            "abandonné", "abandoned", "ruins", "ruines"
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)
        
    @abstractmethod
    def scrape(self, **kwargs) -> List[Dict]:
        """Main scraping method to be implemented by subclasses"""
        pass
        
    def run(self, **kwargs):
        """Run the scraper with error handling"""
        self.logger.info(f"Starting {self.source_name} scraper")
        try:
            spots = self.scrape(**kwargs)
            saved = self.save_spots_batch(spots)
            self.logger.info(f"Saved {saved}/{len(spots)} spots from {self.source_name}")
            return saved
        except Exception as e:
            self.logger.error(f"Scraper failed: {e}")
            raise