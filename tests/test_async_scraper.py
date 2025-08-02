#!/usr/bin/env python3
"""
Unit tests for async scrapers
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from scrapers.async_base_scraper import AsyncBaseScraper
from scrapers.async_reddit_scraper import AsyncRedditScraper


class TestAsyncBaseScraper:
    """Test async base scraper functionality"""
    
    class TestScraper(AsyncBaseScraper):
        """Concrete implementation for testing"""
        async def scrape(self, **kwargs):
            return [{"source": "test", "source_url": "https://test.com"}]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_session_creation(self):
        """Test async session creation"""
        scraper = self.TestScraper("test")
        
        async with scraper.get_session() as session:
            assert session is not None
            assert scraper.session is not None
            assert hasattr(session, 'get')
            assert hasattr(session, 'cookie_jar')
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_with_retry_success(self, async_session_mock):
        """Test successful fetch with retry"""
        scraper = self.TestScraper("test")
        scraper.session = async_session_mock
        
        content = await scraper.fetch_with_retry("https://test.com")
        
        assert content == "Test content"
        assert scraper.rate_limiter.get_stats()['success_count'] == 1
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_with_retry_rate_limit(self, mocker):
        """Test handling rate limit (429) response"""
        scraper = self.TestScraper("test")
        
        # Mock session with 429 response
        session = AsyncMock()
        response = AsyncMock()
        response.status = 429
        session.get.return_value.__aenter__.return_value = response
        scraper.session = session
        
        content = await scraper.fetch_with_retry("https://test.com")
        
        assert content is None
        assert scraper.rate_limiter.get_stats()['rate_limit_count'] >= 1
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_many_concurrent(self, async_session_mock):
        """Test concurrent URL fetching"""
        scraper = self.TestScraper("test")
        scraper.session = async_session_mock
        
        urls = [f"https://test{i}.com" for i in range(10)]
        results = await scraper.fetch_many(urls)
        
        assert len(results) == 10
        assert all(url == expected and content == "Test content" 
                  for (url, content), expected in zip(results, urls))
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_save_spot_async(self, temp_db):
        """Test async spot saving"""
        scraper = self.TestScraper("test", db_path=temp_db)
        
        spot_data = {
            "source": "test",
            "source_url": "https://test.com/spot1",
            "raw_text": "Test spot",
            "latitude": 43.6047,
            "longitude": 1.4442
        }
        
        result = await scraper.save_spot_async(spot_data)
        assert result is True
        
        # Verify in database
        import sqlite3
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM spots WHERE source_url = ?", (spot_data['source_url'],))
        row = cursor.fetchone()
        conn.close()
        
        assert row is not None
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_save_spots_batch(self, temp_db):
        """Test batch spot saving"""
        scraper = self.TestScraper("test", db_path=temp_db)
        
        spots = [
            {
                "source": "test",
                "source_url": f"https://test.com/spot{i}",
                "raw_text": f"Test spot {i}"
            }
            for i in range(5)
        ]
        
        saved_count = await scraper.save_spots_batch_async(spots)
        assert saved_count == 5
    
    @pytest.mark.unit
    def test_extract_coordinates(self):
        """Test coordinate extraction"""
        scraper = self.TestScraper("test")
        
        # Valid coordinates
        text = "Found at 43.6047, 1.4442 near Toulouse"
        coords = scraper.extract_coordinates(text)
        assert coords == (43.6047, 1.4442)
        
        # Invalid coordinates (outside region)
        text = "Paris location: 48.8566, 2.3522"
        coords = scraper.extract_coordinates(text)
        assert coords is None
    
    @pytest.mark.unit
    def test_is_secret_spot(self):
        """Test secret spot detection"""
        scraper = self.TestScraper("test")
        
        secret_texts = [
            "This is a secret swimming spot",
            "Un endroit caché près de la rivière",
            "Abandoned building perfect for urbex"
        ]
        
        for text in secret_texts:
            assert scraper.is_secret_spot(text) is True
        
        normal_text = "Popular tourist destination in Toulouse"
        assert scraper.is_secret_spot(normal_text) is False


class TestAsyncRedditScraper:
    """Test async Reddit scraper"""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_subreddit_async(self, mock_reddit_response):
        """Test Reddit subreddit search"""
        scraper = AsyncRedditScraper()
        
        # Mock fetch_with_retry
        async def mock_fetch(url, **kwargs):
            return json.dumps(mock_reddit_response)
        
        scraper.fetch_with_retry = mock_fetch
        
        spots = await scraper.search_subreddit_async("toulouse", "secret spot")
        
        assert len(spots) == 1
        assert spots[0]['extracted_name'] is not None
        assert spots[0]['latitude'] == 43.5234
        assert spots[0]['longitude'] == 1.4567
        assert spots[0]['is_hidden'] == 1
    
    @pytest.mark.unit
    def test_has_location_keywords(self):
        """Test location keyword detection"""
        scraper = AsyncRedditScraper()
        
        texts_with_location = [
            "GPS coordinates: 43.5, 1.4",
            "Comment y aller: prendre la D817",
            "Cascade près de Saint-Antonin"
        ]
        
        for text in texts_with_location:
            assert scraper.has_location_keywords(text) is True
        
        text_without = "Nice weather today in Toulouse"
        assert scraper.has_location_keywords(text_without) is False
    
    @pytest.mark.unit
    def test_extract_spot_name(self):
        """Test spot name extraction"""
        scraper = AsyncRedditScraper()
        
        # Pattern-based extraction
        text = "Visit the beautiful Cascade de Salles-la-Source"
        name = scraper.extract_spot_name(text)
        assert name == "Cascade de Salles-la-Source"
        
        # Title extraction
        text = "Hidden gem: This amazing viewpoint near Toulouse"
        name = scraper.extract_spot_name(text)
        assert name == "Hidden gem"
    
    @pytest.mark.unit
    def test_extract_activities(self):
        """Test activity extraction"""
        scraper = AsyncRedditScraper()
        
        text = "Perfect for swimming and hiking, also great for camping!"
        activities = scraper.extract_activities(text)
        
        assert "swimming" in activities
        assert "hiking" in activities
        assert "camping" in activities
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_comments_async(self):
        """Test comment fetching"""
        scraper = AsyncRedditScraper()
        
        # Mock response
        mock_comments = [
            {"data": {"body": "Great spot! The coordinates are exactly right."}},
            {"data": {"body": "Be careful, the path is slippery when wet."}}
        ]
        
        async def mock_fetch(url, **kwargs):
            return json.dumps([{}, {"data": {"children": mock_comments}}])
        
        scraper.fetch_with_retry = mock_fetch
        
        comments = await scraper.fetch_comments_async("https://reddit.com/r/toulouse/test")
        
        assert len(comments) == 2
        assert "coordinates" in comments[0]
        assert "slippery" in comments[1]