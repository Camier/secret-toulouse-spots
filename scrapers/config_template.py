#!/usr/bin/env python3
"""
Configuration template for secure credential management
Copy this to config.py and update with your credentials
"""

import os
from pathlib import Path

# Instagram Configuration
# NEVER hardcode credentials in source code!
INSTAGRAM_CONFIG = {
    "username": os.getenv("INSTAGRAM_USERNAME", ""),
    "password": os.getenv("INSTAGRAM_PASSWORD", ""),
    "session_file": Path.home() / ".config" / "weather-app" / "instagram_session.json",
    "delay_range": [3, 7],  # Random delay between requests
    "max_retries": 3,
    "timeout": 30,
}

# Database Configuration
DATABASE_CONFIG = {
    "path": os.getenv("DATABASE_PATH", "hidden_spots.db"),
    "backup_dir": Path.home() / ".local" / "share" / "weather-app" / "backups",
}

# Scraping Configuration
SCRAPING_CONFIG = {
    "camptocamp": {
        "base_url": "https://www.camptocamp.org",
        "max_pages": 5,
        "posts_per_page": 30,
    },
    "instagram_hashtags": [
        # Water-related
        "baignadesauvage",
        "baignadenaturelle",
        "lacdemontagne",
        "cascadefrance",
        "cascadecachee",
        "sourcesecrète",
        # Hiking/outdoor
        "randonnee",
        "randonneefrance",
        "spotsecret",
        "bivouacfrance",
        "spotbivouac",
        "refugesecret",
        # Regional
        "pyrenees",
        "alpes",
        "cevennes",
        "vosges",
        "jura",
        "auvergne",
        "corse",
    ],
    "rate_limits": {"instagram_per_minute": 20, "forum_per_minute": 60},
}

# Security Configuration
SECURITY_CONFIG = {
    "session_file_permissions": 0o600,  # Read/write for owner only
    "config_file_permissions": 0o600,
    "enable_logging": True,
    "log_level": "INFO",
    "log_file": Path.home()
    / ".local"
    / "share"
    / "weather-app"
    / "logs"
    / "scraper.log",
}

# How to use this configuration:
"""
1. Copy this file to config.py
2. Set environment variables:
   export INSTAGRAM_USERNAME="your_username"
   export INSTAGRAM_PASSWORD="your_password"
   
3. Or use a .env file with python-dotenv:
   pip install python-dotenv
   
4. Or use system keyring:
   pip install keyring
   keyring set weather-app instagram_username
   keyring set weather-app instagram_password
"""
