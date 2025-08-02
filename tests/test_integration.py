#!/usr/bin/env python3
"""
Integration tests for the Secret Toulouse Spots system
"""

import pytest
import sqlite3
import asyncio
import json
from pathlib import Path
import time


class TestDatabaseIntegration:
    """Test database operations and integrity"""
    
    @pytest.mark.integration
    def test_database_schema(self, temp_db):
        """Test database has correct schema"""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert 'spots' in tables
        
        # Check indexes exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        assert 'idx_coordinates' in indexes
        assert 'idx_source' in indexes
        assert 'idx_hidden' in indexes
        
        conn.close()
    
    @pytest.mark.integration
    def test_coordinate_index_performance(self, temp_db):
        """Test coordinate index improves query performance"""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Insert test data
        for i in range(1000):
            lat = 43.0 + (i % 100) / 100
            lon = 1.0 + (i % 100) / 100
            cursor.execute("""
                INSERT INTO spots (source, source_url, latitude, longitude)
                VALUES (?, ?, ?, ?)
            """, ('test', f'url{i}', lat, lon))
        conn.commit()
        
        # Test indexed query performance
        start = time.time()
        cursor.execute("""
            SELECT * FROM spots 
            WHERE latitude BETWEEN 43.4 AND 43.6 
            AND longitude BETWEEN 1.4 AND 1.6
        """)
        results = cursor.fetchall()
        indexed_time = time.time() - start
        
        assert len(results) > 0
        assert indexed_time < 0.1  # Should be very fast with index
        
        conn.close()


class TestScraperIntegration:
    """Test scraper components work together"""
    
    @pytest.mark.integration
    def test_validator_with_database(self, temp_db):
        """Test validator integrates with database save"""
        from scrapers.data_validator import SpotDataValidator
        
        validator = SpotDataValidator()
        
        # Valid spot data
        spot = {
            "source": "test",
            "source_url": "https://example.com/spot",
            "raw_text": "Secret waterfall at 43.5234, 1.4567",
            "latitude": 43.5234,
            "longitude": 1.4567,
            "is_hidden": True,
            "difficulty_access": 3
        }
        
        # Validate
        validated = validator.validate(spot)
        
        # Save to database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO spots (
                source, source_url, raw_text, latitude, longitude,
                is_hidden, difficulty_access
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            validated['source'],
            validated['source_url'],
            validated['raw_text'],
            validated['latitude'],
            validated['longitude'],
            validated['is_hidden'],
            validated['difficulty_access']
        ))
        
        conn.commit()
        
        # Verify saved correctly
        cursor.execute("SELECT * FROM spots WHERE source_url = ?", (spot['source_url'],))
        row = cursor.fetchone()
        
        assert row is not None
        assert row[5] == spot['latitude']  # latitude column
        assert row[6] == spot['longitude']  # longitude column
        assert row[9] == 1  # is_hidden converted to int
        
        conn.close()
    
    @pytest.mark.integration
    def test_rate_limiter_with_session_manager(self):
        """Test rate limiter works with session manager"""
        from scrapers.rate_limiter import RateLimiter
        from scrapers.session_manager import SessionManager
        
        limiter = RateLimiter(min_delay=0.1, max_delay=0.5)
        session_mgr = SessionManager("test_integration")
        
        # Clear any existing state
        session_mgr.clear_session_state()
        
        # Simulate scraping session
        for i in range(5):
            limiter.wait_if_needed()
            if i % 2 == 0:
                limiter.record_success()
            else:
                limiter.record_error()
        
        # Save session with rate limiter stats
        state = {
            "rate_limiter_stats": limiter.get_stats(),
            "last_run": time.time()
        }
        session_mgr.save_session_state(state)
        
        # Load and verify
        loaded = session_mgr.load_session_state()
        assert loaded is not None
        assert loaded['rate_limiter_stats']['success_count'] == 3
        assert loaded['rate_limiter_stats']['error_count'] == 2
        
        # Cleanup
        session_mgr.clear_session_state()


class TestMapIntegration:
    """Test map visualization components"""
    
    @pytest.mark.integration
    def test_map_files_exist(self):
        """Test all map files are present"""
        map_files = [
            "map.html",
            "enhanced-map.html",
            "viewport-optimized-map.html"
        ]
        
        for file in map_files:
            assert Path(file).exists(), f"Map file {file} not found"
    
    @pytest.mark.integration
    def test_map_clustering_config(self):
        """Test map has clustering configuration"""
        with open("enhanced-map.html", "r") as f:
            content = f.read()
        
        # Check for clustering setup
        assert "L.markerClusterGroup" in content
        assert "chunkedLoading: true" in content
        assert "removeOutsideVisibleBounds: true" in content
        assert "disableClusteringAtZoom: 16" in content
    
    @pytest.mark.integration
    def test_viewport_optimization(self):
        """Test viewport map has optimization features"""
        with open("viewport-optimized-map.html", "r") as f:
            content = f.read()
        
        # Check for viewport features
        assert "isInBounds" in content
        assert "renderVisibleMarkers" in content
        assert "performanceMode" in content
        assert "bounds.pad" in content


class TestAsyncScraperIntegration:
    """Test async scraper integration"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_async_scraper_full_flow(self, temp_db):
        """Test complete async scraping flow"""
        from scrapers.async_base_scraper import AsyncBaseScraper
        
        class TestIntegrationScraper(AsyncBaseScraper):
            async def scrape(self, **kwargs):
                # Simulate finding spots
                return [
                    {
                        "source": "test",
                        "source_url": f"https://test.com/spot{i}",
                        "raw_text": f"Secret spot {i} at 43.{i}, 1.{i}",
                        "latitude": 43.0 + i/10,
                        "longitude": 1.0 + i/10
                    }
                    for i in range(5)
                ]
        
        scraper = TestIntegrationScraper("test_integration", db_path=temp_db)
        
        # Run scraper
        saved = await scraper.run()
        
        assert saved == 5
        
        # Verify in database
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM spots")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 5


class TestAntiDetectionIntegration:
    """Test anti-detection integration"""
    
    @pytest.mark.integration
    def test_fingerprint_with_selenium_options(self):
        """Test fingerprint integrates with Selenium options"""
        from scrapers.anti_detection import AntiDetectionManager
        
        manager = AntiDetectionManager()
        fingerprint = manager.generate_browser_fingerprint()
        options = manager.get_selenium_options(fingerprint)
        
        # Verify consistency
        window_size_opt = next(opt for opt in options if '--window-size=' in opt)
        expected_size = f"{fingerprint['screen']['width']},{fingerprint['screen']['height']}"
        assert expected_size in window_size_opt
        
        # Verify anti-detection flags
        assert '--disable-blink-features=AutomationControlled' in options
        assert any('--user-agent=' in opt for opt in options)