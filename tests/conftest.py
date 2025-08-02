#!/usr/bin/env python3
"""
Pytest configuration and fixtures
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    # Create schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_url TEXT UNIQUE,
            raw_text TEXT,
            extracted_name TEXT,
            latitude REAL,
            longitude REAL,
            location_type TEXT,
            activities TEXT,
            is_hidden INTEGER DEFAULT 0,
            difficulty_access INTEGER DEFAULT 1,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSON
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_coordinates ON spots(latitude, longitude)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON spots(source)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hidden ON spots(is_hidden)")
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_spot_data():
    """Sample spot data for testing"""
    return {
        "source": "test",
        "source_url": "https://example.com/spot1",
        "raw_text": "A beautiful hidden waterfall near Toulouse",
        "extracted_name": "Cascade Secrète",
        "latitude": 43.6047,
        "longitude": 1.4442,
        "location_type": "waterfall",
        "activities": "swimming, hiking",
        "is_hidden": 1,
        "metadata": {
            "author": "test_user",
            "date": "2024-01-15"
        }
    }


@pytest.fixture
def mock_reddit_response():
    """Mock Reddit API response"""
    return {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "Secret swimming spot near Toulouse",
                        "selftext": "Found this amazing hidden cascade at 43.5234, 1.4567. Perfect for swimming!",
                        "permalink": "/r/toulouse/comments/test123",
                        "author": "test_user",
                        "score": 42,
                        "num_comments": 5,
                        "created_utc": 1642000000
                    }
                }
            ]
        }
    }


@pytest.fixture
def rate_limiter():
    """Create rate limiter for testing"""
    from scrapers.rate_limiter import RateLimiter
    return RateLimiter(
        min_delay=0.1,
        max_delay=0.5,
        max_retries=2,
        backoff_factor=2.0
    )


@pytest.fixture
def async_session_mock(mocker):
    """Mock aiohttp session"""
    session = mocker.AsyncMock()
    response = mocker.AsyncMock()
    response.status = 200
    response.text.return_value = "Test content"
    session.get.return_value.__aenter__.return_value = response
    return session