#!/usr/bin/env python3
"""
Async base scraper for improved performance
Uses aiohttp for concurrent requests
"""

import asyncio
import aiohttp
import json
import logging
import random
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from contextlib import asynccontextmanager

# Import enhanced modules
from .data_validator import SpotDataValidator
from .rate_limiter import RateLimiter, ScraperRateLimiters
from .session_manager import SessionManager

# User agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]


class AsyncBaseScraper(ABC):
    """Async base class for high-performance scrapers"""
    
    def __init__(self, source_name: str, db_path: str = "../hidden_spots.db"):
        self.source_name = source_name
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize components
        self.validator = SpotDataValidator()
        self.session_manager = SessionManager(f"async_{source_name}")
        
        # Rate limiter based on source
        if source_name == 'instagram':
            self.rate_limiter = ScraperRateLimiters.instagram()
        elif source_name == 'reddit':
            self.rate_limiter = ScraperRateLimiters.reddit()
        else:
            self.rate_limiter = ScraperRateLimiters.osm()
            
        # Async session will be created in context manager
        self.session = None
        self.semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests
        
    @asynccontextmanager
    async def get_session(self):
        """Async context manager for aiohttp session"""
        # Create connector with connection pooling
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Per-host connection limit
            ttl_dns_cache=300  # DNS cache timeout
        )
        
        # Create session with timeout
        timeout = aiohttp.ClientTimeout(total=30)
        
        # Random user agent
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=headers
        ) as session:
            # Load saved cookies if available
            saved_state = self.session_manager.load_session_state()
            if saved_state and 'cookies' in saved_state:
                session.cookie_jar.update_cookies(saved_state['cookies'])
                
            self.session = session
            yield session
            
            # Save session state
            cookies = {
                cookie.key: cookie.value 
                for cookie in session.cookie_jar 
            }
            self.session_manager.save_session_state({
                'cookies': cookies,
                'last_run': datetime.now().isoformat()
            })
            
    async def fetch_with_retry(self, url: str, **kwargs) -> Optional[str]:
        """Fetch URL with rate limiting and retry logic"""
        async with self.semaphore:  # Limit concurrent requests
            # Apply rate limiting
            await asyncio.sleep(self.rate_limiter._get_random_delay())
            
            for attempt in range(self.rate_limiter.max_retries):
                try:
                    # Rotate user agent occasionally
                    if random.random() < 0.1:
                        self.session.headers['User-Agent'] = random.choice(USER_AGENTS)
                        
                    async with self.session.get(url, **kwargs) as response:
                        if response.status == 200:
                            self.rate_limiter.record_success()
                            return await response.text()
                        elif response.status == 429:  # Rate limited
                            self.rate_limiter.record_error(is_rate_limit=True)
                            wait_time = self.rate_limiter.min_delay * (2 ** attempt)
                            self.logger.warning(f"Rate limited, waiting {wait_time}s")
                            await asyncio.sleep(wait_time)
                        else:
                            self.rate_limiter.record_error()
                            self.logger.error(f"HTTP {response.status} for {url}")
                            
                except asyncio.TimeoutError:
                    self.logger.error(f"Timeout fetching {url}")
                    self.rate_limiter.record_error()
                except Exception as e:
                    self.logger.error(f"Error fetching {url}: {e}")
                    self.rate_limiter.record_error()
                    
                if attempt < self.rate_limiter.max_retries - 1:
                    await asyncio.sleep(self.rate_limiter.min_delay * (2 ** attempt))
                    
        return None
        
    async def fetch_many(self, urls: List[str]) -> List[Tuple[str, Optional[str]]]:
        """Fetch multiple URLs concurrently"""
        tasks = [self.fetch_with_retry(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Pair URLs with results
        return [
            (url, result if not isinstance(result, Exception) else None)
            for url, result in zip(urls, results)
        ]
        
    def get_db_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        db_file = self.db_path if self.db_path.is_absolute() else Path(__file__).parent / self.db_path
        return sqlite3.connect(str(db_file))
        
    async def save_spot_async(self, spot_data: Dict) -> bool:
        """Save spot asynchronously (runs in thread pool)"""
        # Validate data
        try:
            validated_data = self.validator.validate(spot_data)
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return False
            
        # Run database operation in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._save_spot_sync, validated_data)
        
    def _save_spot_sync(self, spot_data: Dict) -> bool:
        """Synchronous save operation for thread pool"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
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
            
    async def save_spots_batch_async(self, spots: List[Dict]) -> int:
        """Save multiple spots concurrently"""
        tasks = [self.save_spot_async(spot) for spot in spots]
        results = await asyncio.gather(*tasks)
        return sum(1 for r in results if r)
        
    def extract_coordinates(self, text: str) -> Optional[Tuple[float, float]]:
        """Extract coordinates from text"""
        import re
        
        coord_pattern = r"(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)"
        match = re.search(coord_pattern, text)
        
        if match:
            lat, lon = float(match.group(1)), float(match.group(2))
            # Validate Toulouse region
            if 42.5 <= lat <= 44.5 and -1.0 <= lon <= 3.0:
                return lat, lon
        return None
        
    def is_secret_spot(self, text: str) -> bool:
        """Check if text indicates a secret spot"""
        keywords = [
            "secret", "caché", "cachée", "hidden", "peu connu",
            "méconnu", "confidentiel", "discret", "insolite",
            "abandonné", "abandoned", "ruins", "ruines"
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)
        
    @abstractmethod
    async def scrape(self, **kwargs) -> List[Dict]:
        """Main async scraping method to be implemented"""
        pass
        
    async def run(self, **kwargs):
        """Run the async scraper"""
        self.logger.info(f"Starting async {self.source_name} scraper")
        
        try:
            async with self.get_session():
                spots = await self.scrape(**kwargs)
                saved = await self.save_spots_batch_async(spots)
                self.logger.info(f"Saved {saved}/{len(spots)} spots from {self.source_name}")
                
                # Log stats
                stats = self.rate_limiter.get_stats()
                self.logger.info(f"Rate limiter stats: {stats}")
                
                return saved
                
        except Exception as e:
            self.logger.error(f"Async scraper failed: {e}")
            raise


class SessionManager:
    """Simple session state manager for async scrapers"""
    
    def __init__(self, session_name: str):
        self.session_name = session_name
        self.state_file = Path(f"sessions/{session_name}_state.json")
        self.state_file.parent.mkdir(exist_ok=True)
        
    def save_session_state(self, state: Dict):
        """Save session state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            logging.error(f"Failed to save session state: {e}")
            
    def load_session_state(self) -> Optional[Dict]:
        """Load session state from file"""
        if not self.state_file.exists():
            return None
            
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load session state: {e}")
            return None