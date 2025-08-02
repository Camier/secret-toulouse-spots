#!/usr/bin/env python3
"""
Unit tests for rate limiter
"""

import pytest
import time
from scrapers.rate_limiter import RateLimiter, ScraperRateLimiters


class TestRateLimiter:
    """Test rate limiting functionality"""
    
    @pytest.mark.unit
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization"""
        limiter = RateLimiter(
            min_delay=1.0,
            max_delay=5.0,
            max_retries=3,
            backoff_factor=2.0
        )
        
        assert limiter.min_delay == 1.0
        assert limiter.max_delay == 5.0
        assert limiter.max_retries == 3
        assert limiter.backoff_factor == 2.0
    
    @pytest.mark.unit
    def test_delay_calculation(self, rate_limiter):
        """Test delay calculation stays within bounds"""
        for _ in range(100):
            delay = rate_limiter._get_random_delay()
            assert rate_limiter.min_delay <= delay <= rate_limiter.max_delay
    
    @pytest.mark.unit
    def test_wait_if_needed_respects_delay(self, rate_limiter):
        """Test wait_if_needed enforces minimum delay"""
        # First request - no wait
        start = time.time()
        rate_limiter.wait_if_needed()
        elapsed = time.time() - start
        assert elapsed < 0.1  # Should be instant
        
        # Second request - should wait
        start = time.time()
        rate_limiter.wait_if_needed()
        elapsed = time.time() - start
        assert elapsed >= rate_limiter.min_delay * 0.9  # Allow 10% tolerance
    
    @pytest.mark.unit
    def test_error_tracking(self, rate_limiter):
        """Test error counting and stats"""
        # Record some errors
        rate_limiter.record_error()
        rate_limiter.record_error()
        rate_limiter.record_error(is_rate_limit=True)
        
        stats = rate_limiter.get_stats()
        assert stats['error_count'] == 3
        assert stats['rate_limit_count'] == 1
    
    @pytest.mark.unit
    def test_success_tracking(self, rate_limiter):
        """Test success counting"""
        rate_limiter.record_success()
        rate_limiter.record_success()
        
        stats = rate_limiter.get_stats()
        assert stats['success_count'] == 2
    
    @pytest.mark.unit
    def test_should_retry(self, rate_limiter):
        """Test retry logic"""
        # Should retry on first attempts
        assert rate_limiter.should_retry(0) is True
        assert rate_limiter.should_retry(1) is True
        
        # Should not retry beyond max_retries
        assert rate_limiter.should_retry(rate_limiter.max_retries) is False
    
    @pytest.mark.unit
    def test_reset_stats(self, rate_limiter):
        """Test stats reset"""
        # Add some stats
        rate_limiter.record_error()
        rate_limiter.record_success()
        
        # Reset
        rate_limiter.reset_stats()
        
        stats = rate_limiter.get_stats()
        assert stats['error_count'] == 0
        assert stats['success_count'] == 0
        assert stats['rate_limit_count'] == 0


class TestScraperRateLimiters:
    """Test scraper-specific rate limiters"""
    
    @pytest.mark.unit
    def test_instagram_rate_limiter(self):
        """Test Instagram rate limiter configuration"""
        limiter = ScraperRateLimiters.instagram()
        
        assert limiter.min_delay == 3.0
        assert limiter.max_delay == 8.0
        assert limiter.max_retries == 3
        assert limiter.backoff_factor == 2.0
    
    @pytest.mark.unit
    def test_reddit_rate_limiter(self):
        """Test Reddit rate limiter configuration"""
        limiter = ScraperRateLimiters.reddit()
        
        assert limiter.min_delay == 2.0
        assert limiter.max_delay == 5.0
        assert limiter.max_retries == 5
        assert limiter.backoff_factor == 1.5
    
    @pytest.mark.unit
    def test_osm_rate_limiter(self):
        """Test OSM rate limiter configuration"""
        limiter = ScraperRateLimiters.osm()
        
        assert limiter.min_delay == 1.0
        assert limiter.max_delay == 3.0
        assert limiter.max_retries == 3
        assert limiter.backoff_factor == 2.0
    
    @pytest.mark.unit
    def test_custom_rate_limiter(self):
        """Test custom rate limiter creation"""
        limiter = ScraperRateLimiters.custom(
            min_delay=0.5,
            max_delay=2.0,
            max_retries=10
        )
        
        assert limiter.min_delay == 0.5
        assert limiter.max_delay == 2.0
        assert limiter.max_retries == 10