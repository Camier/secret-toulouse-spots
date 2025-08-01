"""
Scraper configuration settings
Load from environment variables with sensible defaults
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScraperConfig:
    # Reddit settings
    reddit_client_id: Optional[str] = os.getenv('REDDIT_CLIENT_ID')
    reddit_client_secret: Optional[str] = os.getenv('REDDIT_CLIENT_SECRET')
    reddit_user_agent: str = os.getenv('REDDIT_USER_AGENT', 'SecretSpotsScraper/1.0')
    
    # Instagram settings
    instagram_username: Optional[str] = os.getenv('INSTAGRAM_USERNAME')
    instagram_password: Optional[str] = os.getenv('INSTAGRAM_PASSWORD')
    
    # Request settings
    request_timeout: int = int(os.getenv('REQUEST_TIMEOUT', '30'))
    max_retries: int = int(os.getenv('MAX_RETRIES', '3'))
    
    # Selenium settings
    headless_mode: bool = os.getenv('HEADLESS_MODE', 'true').lower() == 'true'
    webdriver_path: Optional[str] = os.getenv('WEBDRIVER_PATH')
    
    # Rate limiting
    min_delay: float = float(os.getenv('MIN_DELAY', '1.0'))
    max_delay: float = float(os.getenv('MAX_DELAY', '3.0'))
    
    # Database
    db_path: str = os.getenv('DB_PATH', '../hidden_spots.db')
    
    # Logging
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_file: Optional[str] = os.getenv('LOG_FILE')


# Singleton instance
config = ScraperConfig()
