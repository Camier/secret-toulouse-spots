#!/usr/bin/env python3
"""
Enhanced rate limiting with exponential backoff
"""

import time
import random
import logging
from typing import Optional, Callable
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RateLimiter:
    """Advanced rate limiter with exponential backoff and circuit breaker pattern"""
    
    def __init__(self, 
                 min_delay: float = 1.0,
                 max_delay: float = 3.0,
                 backoff_factor: float = 2.0,
                 max_retries: int = 5,
                 circuit_breaker_threshold: int = 10,
                 reset_time: int = 300):  # 5 minutes
        """
        Initialize rate limiter with configurable parameters
        
        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            backoff_factor: Exponential backoff multiplier
            max_retries: Maximum number of retries before giving up
            circuit_breaker_threshold: Errors before circuit opens
            reset_time: Time in seconds before resetting error count
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.max_retries = max_retries
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.reset_time = reset_time
        
        # State tracking
        self.consecutive_errors = 0
        self.total_errors = 0
        self.last_error_time = None
        self.circuit_open = False
        self.last_request_time = None
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.rate_limited_count = 0
        
    def wait(self):
        """Apply rate limiting delay with jitter"""
        # Calculate base delay
        if self.consecutive_errors > 0:
            # Exponential backoff
            delay = min(
                self.min_delay * (self.backoff_factor ** self.consecutive_errors),
                self.max_delay * 10  # Cap at 10x max delay
            )
        else:
            # Normal random delay
            delay = random.uniform(self.min_delay, self.max_delay)
        
        # Add jitter (±20%)
        jitter = delay * 0.2 * (2 * random.random() - 1)
        final_delay = max(0.1, delay + jitter)  # Minimum 100ms
        
        logger.debug(f"Rate limiting: waiting {final_delay:.2f}s")
        time.sleep(final_delay)
        self.last_request_time = datetime.now()
        
    def record_success(self):
        """Record a successful request"""
        self.consecutive_errors = 0
        self.successful_requests += 1
        self.total_requests += 1
        
        # Check if we should reset circuit breaker
        if self.circuit_open and self._should_reset_circuit():
            self.circuit_open = False
            logger.info("Circuit breaker reset")
            
    def record_error(self, is_rate_limit: bool = False):
        """Record an error/rate limit"""
        self.consecutive_errors += 1
        self.total_errors += 1
        self.total_requests += 1
        self.last_error_time = datetime.now()
        
        if is_rate_limit:
            self.rate_limited_count += 1
            logger.warning(f"Rate limited! Consecutive errors: {self.consecutive_errors}")
        
        # Check circuit breaker
        if self.consecutive_errors >= self.circuit_breaker_threshold:
            self.circuit_open = True
            logger.error(f"Circuit breaker opened after {self.consecutive_errors} consecutive errors")
            
    def _should_reset_circuit(self) -> bool:
        """Check if enough time has passed to reset circuit"""
        if not self.last_error_time:
            return True
            
        time_since_error = (datetime.now() - self.last_error_time).total_seconds()
        return time_since_error > self.reset_time
        
    def is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self.circuit_open and self._should_reset_circuit():
            self.circuit_open = False
            self.consecutive_errors = 0
            
        return self.circuit_open
        
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Optional[any]:
        """Execute function with automatic retry and rate limiting"""
        for attempt in range(self.max_retries):
            # Check circuit breaker
            if self.is_circuit_open():
                logger.error("Circuit breaker is open, skipping request")
                return None
                
            # Apply rate limiting
            self.wait()
            
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
                
            except Exception as e:
                error_msg = str(e).lower()
                is_rate_limit = any(term in error_msg for term in [
                    'rate limit', 'too many requests', '429', 'throttle'
                ])
                
                self.record_error(is_rate_limit)
                
                if attempt < self.max_retries - 1:
                    wait_time = self.min_delay * (self.backoff_factor ** (attempt + 1))
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.max_retries}), "
                        f"waiting {wait_time:.1f}s before retry: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Max retries reached, giving up: {e}")
                    raise
                    
        return None
        
    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        success_rate = (
            self.successful_requests / self.total_requests * 100
            if self.total_requests > 0 else 0
        )
        
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'total_errors': self.total_errors,
            'rate_limited_count': self.rate_limited_count,
            'success_rate': f"{success_rate:.1f}%",
            'circuit_breaker_open': self.circuit_open,
            'consecutive_errors': self.consecutive_errors
        }
        
    def reset_stats(self):
        """Reset statistics (but not error counters)"""
        self.total_requests = 0
        self.successful_requests = 0
        self.rate_limited_count = 0


# Example usage for different scenarios
class ScraperRateLimiters:
    """Pre-configured rate limiters for different scrapers"""
    
    @staticmethod
    def instagram():
        """Instagram requires careful rate limiting"""
        return RateLimiter(
            min_delay=2.0,
            max_delay=5.0,
            backoff_factor=2.5,
            max_retries=3,
            circuit_breaker_threshold=5
        )
        
    @staticmethod
    def reddit():
        """Reddit API has clear rate limits"""
        return RateLimiter(
            min_delay=1.0,
            max_delay=2.0,
            backoff_factor=2.0,
            max_retries=5,
            circuit_breaker_threshold=10
        )
        
    @staticmethod
    def osm():
        """OSM is generally more lenient"""
        return RateLimiter(
            min_delay=0.5,
            max_delay=1.5,
            backoff_factor=1.5,
            max_retries=3,
            circuit_breaker_threshold=15
        )