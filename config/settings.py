#!/usr/bin/env python3
"""
Application settings and configuration management
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class DatabaseConfig:
    """Database configuration"""
    path: str = "hidden_spots.db"
    
    # Connection pool settings
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    
    # Query settings
    query_timeout: int = 30
    enable_foreign_keys: bool = True
    
    def get_connection_string(self) -> str:
        """Get SQLite connection string"""
        return f"sqlite:///{self.path}"


@dataclass
class ScraperConfig:
    """Scraper configuration"""
    # Rate limiting
    min_delay: float = 2.0
    max_delay: float = 5.0
    max_retries: int = 3
    backoff_factor: float = 2.0
    
    # Concurrent requests
    max_concurrent_requests: int = 5
    request_timeout: int = 30
    
    # User agents
    rotate_user_agents: bool = True
    user_agent_rotation_rate: float = 0.1
    
    # Session management
    session_expire_hours: int = 24
    persist_cookies: bool = True
    
    # Anti-detection
    enable_anti_detection: bool = True
    randomize_fingerprint: bool = True
    simulate_human_behavior: bool = True


@dataclass
class RedditConfig(ScraperConfig):
    """Reddit-specific configuration"""
    name: str = "reddit"
    
    # API settings
    subreddits: list = field(default_factory=lambda: [
        "toulouse", "Toulouse", "hautegaronne", "Occitanie",
        "randonee", "camping", "urbex", "france"
    ])
    
    search_terms: list = field(default_factory=lambda: [
        "spot secret", "endroit caché", "lieu abandonné",
        "baignade sauvage", "spot baignade", "cascade",
        "point de vue", "randonnée", "urbex toulouse"
    ])
    
    # Rate limiting overrides
    min_delay: float = 2.0
    max_delay: float = 5.0


@dataclass
class InstagramConfig(ScraperConfig):
    """Instagram-specific configuration"""
    name: str = "instagram"
    
    # Rate limiting overrides (stricter)
    min_delay: float = 3.0
    max_delay: float = 8.0
    
    # Instagram specific
    hashtags: list = field(default_factory=lambda: [
        "#toulousesecret", "#spotsecret", "#toulousehidden"
    ])


@dataclass
class MapConfig:
    """Map visualization configuration"""
    # Clustering
    enable_clustering: bool = True
    disable_clustering_zoom: int = 16
    cluster_radius: int = 80
    
    # Performance
    chunk_size: int = 100
    progressive_loading: bool = True
    viewport_optimization: bool = True
    viewport_padding: float = 0.2
    
    # Map settings
    default_center: tuple = (43.6047, 1.4442)  # Toulouse
    default_zoom: int = 11
    min_zoom: int = 7
    max_zoom: int = 18


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    console: bool = True
    file: bool = True
    structured: bool = False
    
    # File settings
    log_dir: str = "logs"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    # Log levels per module
    module_levels: dict = field(default_factory=lambda: {
        "scrapers": "DEBUG",
        "validators": "INFO",
        "database": "WARNING"
    })


@dataclass
class AppConfig:
    """Main application configuration"""
    # Sub-configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    map: MapConfig = field(default_factory=MapConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Scraper configurations
    reddit: RedditConfig = field(default_factory=RedditConfig)
    instagram: InstagramConfig = field(default_factory=InstagramConfig)
    
    # General settings
    debug: bool = False
    testing: bool = False
    
    # Data validation
    coordinate_bounds: dict = field(default_factory=lambda: {
        "min_lat": 42.5,
        "max_lat": 44.5,
        "min_lon": -1.0,
        "max_lon": 3.0
    })
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AppConfig':
        """Create from dictionary"""
        # Handle nested configs
        if 'database' in data:
            data['database'] = DatabaseConfig(**data['database'])
        if 'map' in data:
            data['map'] = MapConfig(**data['map'])
        if 'logging' in data:
            data['logging'] = LoggingConfig(**data['logging'])
        if 'reddit' in data:
            data['reddit'] = RedditConfig(**data['reddit'])
        if 'instagram' in data:
            data['instagram'] = InstagramConfig(**data['instagram'])
            
        return cls(**data)


class ConfigManager:
    """Manage application configuration"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
        
    def _load_config(self) -> AppConfig:
        """Load configuration from file and environment"""
        # Start with defaults
        config = AppConfig()
        
        # Load from file if exists
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                file_config = json.load(f)
                config = AppConfig.from_dict(file_config)
        
        # Override with environment variables
        self._apply_env_overrides(config)
        
        return config
    
    def _apply_env_overrides(self, config: AppConfig):
        """Apply environment variable overrides"""
        # Database
        if db_path := os.getenv("SPOTS_DB_PATH"):
            config.database.path = db_path
            
        # Logging
        if log_level := os.getenv("SPOTS_LOG_LEVEL"):
            config.logging.level = log_level
        if log_dir := os.getenv("SPOTS_LOG_DIR"):
            config.logging.log_dir = log_dir
            
        # Debug mode
        if debug := os.getenv("SPOTS_DEBUG"):
            config.debug = debug.lower() in ("true", "1", "yes")
            
        # Testing mode
        if testing := os.getenv("SPOTS_TESTING"):
            config.testing = testing.lower() in ("true", "1", "yes")
            
        # Scraper settings
        if max_concurrent := os.getenv("SPOTS_MAX_CONCURRENT"):
            config.reddit.max_concurrent_requests = int(max_concurrent)
            config.instagram.max_concurrent_requests = int(max_concurrent)
    
    def save_config(self):
        """Save current configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config.to_dict(), f, indent=2)
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation path"""
        parts = path.split('.')
        value = self.config
        
        try:
            for part in parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return default
            return value
        except (AttributeError, TypeError):
            return default
    
    def set(self, path: str, value: Any):
        """Set configuration value by dot-notation path"""
        parts = path.split('.')
        obj = self.config
        
        # Navigate to parent
        for part in parts[:-1]:
            obj = getattr(obj, part)
            
        # Set value
        setattr(obj, parts[-1], value)
    
    def get_scraper_config(self, scraper_name: str) -> Optional[ScraperConfig]:
        """Get configuration for a specific scraper"""
        return getattr(self.config, scraper_name, None)


# Global configuration instance
_config_manager = None


def get_config() -> ConfigManager:
    """Get global configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_settings() -> AppConfig:
    """Get application settings"""
    return get_config().config


# Environment-specific configurations
def load_env_config():
    """Load environment-specific configuration"""
    env = os.getenv("SPOTS_ENV", "development")
    
    env_configs = {
        "development": {
            "debug": True,
            "logging": {"level": "DEBUG"},
            "database": {"path": "dev_spots.db"}
        },
        "production": {
            "debug": False,
            "logging": {"level": "INFO", "structured": True},
            "database": {"path": "/var/lib/toulouse_spots/spots.db"}
        },
        "testing": {
            "testing": True,
            "logging": {"level": "DEBUG", "file": False},
            "database": {"path": ":memory:"}
        }
    }
    
    if env in env_configs:
        config = get_config()
        for key, value in env_configs[env].items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    config.set(f"{key}.{subkey}", subvalue)
            else:
                config.set(key, value)