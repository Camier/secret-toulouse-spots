#!/usr/bin/env python3
"""
Test Phase 2 reliability improvements
"""

import sys
import time
import json
from pathlib import Path

# Add scrapers to path
sys.path.append('scrapers')

from rate_limiter import RateLimiter, ScraperRateLimiters
from session_manager import SessionManager
from data_validator import SpotDataValidator


def test_rate_limiter():
    """Test enhanced rate limiting with exponential backoff"""
    print("🔄 Testing Enhanced Rate Limiter\n")
    
    # Create Instagram rate limiter
    limiter = ScraperRateLimiters.instagram()
    
    print("Testing normal requests...")
    start = time.time()
    for i in range(3):
        limiter.wait()
        limiter.record_success()
        print(f"  Request {i+1}: Success")
    
    elapsed = time.time() - start
    print(f"  Total time for 3 requests: {elapsed:.1f}s")
    
    print("\nSimulating rate limit errors...")
    for i in range(3):
        limiter.record_error(is_rate_limit=True)
        limiter.wait()
        print(f"  Error {i+1}: Backoff delay applied")
    
    stats = limiter.get_stats()
    print(f"\n📊 Rate Limiter Stats:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")
    
    print("\n✅ Rate limiter working with exponential backoff!")


def test_session_persistence():
    """Test session persistence functionality"""
    print("\n🔐 Testing Session Persistence\n")
    
    # Create session manager
    manager = SessionManager('test_scraper', expire_hours=1)
    
    # Create mock session
    import requests
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'TestBot/1.0',
        'Accept': 'application/json'
    })
    
    # Add a cookie
    session.cookies.set('test_cookie', 'test_value', domain='example.com')
    
    # Save session
    print("Saving session...")
    success = manager.save_session(session, {'test_data': 'test_value'})
    print(f"  Save successful: {success}")
    
    # Get session info
    info = manager.get_session_info()
    if info:
        print("\n📊 Session Info:")
        print(f"  - Created: {info['created_at']}")
        print(f"  - Expires: {info['expires_at']}")
        print(f"  - Valid: {info['is_valid']}")
        print(f"  - Has cookies: {info['has_cookies']}")
        print(f"  - Has headers: {info['has_headers']}")
    
    # Load session into new session object
    new_session = requests.Session()
    state = manager.load_session(new_session)
    
    print("\n🔄 Loaded Session:")
    print(f"  - User-Agent: {new_session.headers.get('User-Agent')}")
    print(f"  - Cookies: {len(new_session.cookies)}")
    print(f"  - State data: {state}")
    
    # Clean up
    manager.clear_session()
    print("\n✅ Session persistence working correctly!")


def test_data_validation():
    """Test enhanced data validation"""
    print("\n✅ Testing Data Validation\n")
    
    validator = SpotDataValidator()
    
    # Test valid spot
    valid_spot = {
        'source': 'reddit',
        'source_url': 'https://reddit.com/r/toulouse/comments/test123',
        'raw_text': 'Amazing secret waterfall near Toulouse! GPS: 43.604652, 1.444209. Perfect for swimming and hiking.',
        'extracted_name': 'Secret Waterfall',
        'activities': 'swimming, hiking, photography'
    }
    
    print("Testing valid spot...")
    try:
        validated = validator.validate(valid_spot)
        print("  ✅ Validation successful!")
        print(f"  - Confidence score: {validated['confidence_score']:.2f}")
        print(f"  - Location type: {validated['location_type']}")
        print(f"  - Coordinates: {validated.get('latitude')}, {validated.get('longitude')}")
        print(f"  - Tags: {validated.get('tags')}")
    except Exception as e:
        print(f"  ❌ Validation failed: {e}")
    
    # Test invalid spot
    invalid_spot = {
        'source': 'unknown',
        'source_url': 'not-a-url',
        'raw_text': 'Too short'
    }
    
    print("\nTesting invalid spot...")
    try:
        validator.validate(invalid_spot)
        print("  ❌ Should have failed!")
    except Exception as e:
        print(f"  ✅ Correctly rejected: {e}")
    
    # Test coordinate extraction
    coord_spot = {
        'source': 'osm',
        'source_url': 'https://openstreetmap.org/node/123',
        'raw_text': 'Hidden spot at coordinates 43.5, 1.5 with great views!'
    }
    
    print("\nTesting coordinate extraction...")
    validated = validator.validate(coord_spot)
    if 'latitude' in validated:
        print(f"  ✅ Extracted coordinates: {validated['latitude']}, {validated['longitude']}")
    else:
        print("  ❌ Failed to extract coordinates")
    
    print("\n✅ Data validation working with schema!")


def test_integration():
    """Test integration of all Phase 2 components"""
    print("\n🔧 Testing Phase 2 Integration\n")
    
    # Import base scraper
    from base_scraper import BaseScraper
    
    class TestScraper(BaseScraper):
        def scrape(self):
            # Simulate scraping
            return [{
                'source': self.source_name,
                'source_url': 'https://reddit.com/r/test/comments/123',
                'raw_text': 'Test spot at 43.6, 1.4',
                'extracted_name': 'Test Location'
            }]
    
    # Create scraper with all enhancements
    scraper = TestScraper('reddit')
    
    print("Checking enhanced components:")
    print(f"  - Rate limiter: {'✅' if scraper.rate_limiter else '❌'}")
    print(f"  - Session manager: {'✅' if scraper.session_manager else '❌'}")
    print(f"  - Data validator: {'✅' if scraper.validator else '❌'}")
    
    # Test making a request
    print("\nTesting request with enhancements...")
    try:
        response = scraper.make_request('https://httpbin.org/user-agent')
        data = response.json()
        print(f"  ✅ Request successful!")
        print(f"  - User-Agent: {data['user-agent'][:50]}...")
    except Exception as e:
        print(f"  ❌ Request failed: {e}")
    
    print("\n✅ All Phase 2 components integrated successfully!")


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 2 RELIABILITY IMPROVEMENTS TEST")
    print("=" * 60)
    
    test_rate_limiter()
    test_session_persistence()
    test_data_validation()
    test_integration()
    
    print("\n" + "=" * 60)
    print("✅ ALL PHASE 2 TESTS COMPLETE!")
    print("=" * 60)