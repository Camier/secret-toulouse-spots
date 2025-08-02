#!/usr/bin/env python3
"""
Test user-agent rotation functionality
"""

import sys
import random
sys.path.append('scrapers')

from base_scraper import BaseScraper

class TestScraper(BaseScraper):
    """Test scraper to verify user-agent rotation"""
    
    def scrape(self):
        """Dummy scrape method"""
        pass

def test_user_agent_rotation():
    """Test that user agents are rotating properly"""
    
    # Create test scraper
    scraper = TestScraper("test")
    
    print("🔄 Testing User-Agent Rotation\n")
    
    # Get initial user agent
    initial_agent = scraper.session.headers.get('User-Agent')
    print(f"Initial User-Agent: {initial_agent[:80]}...")
    
    # Track unique user agents
    seen_agents = {initial_agent}
    
    # Make multiple requests to trigger rotation
    print("\n📡 Making 50 test requests (10% rotation chance)...")
    rotations = 0
    
    for i in range(50):
        current_agent = scraper.session.headers.get('User-Agent')
        
        # Simulate rotation check without actual network request
        if random.random() < 0.1:
            scraper._rotate_user_agent()
        
        new_agent = scraper.session.headers.get('User-Agent')
        
        if new_agent != current_agent:
            rotations += 1
            print(f"  ✅ Rotation #{rotations}: {new_agent[:60]}...")
            seen_agents.add(new_agent)
    
    print(f"\n📊 Summary:")
    print(f"  - Total requests: 50")
    print(f"  - User-agent rotations: {rotations}")
    print(f"  - Unique user agents seen: {len(seen_agents)}")
    print(f"  - Rotation rate: {rotations/50*100:.1f}% (expected ~10%)")
    
    # Test forced rotation
    print("\n🔧 Testing forced rotation...")
    for i in range(5):
        scraper._rotate_user_agent()
        agent = scraper.session.headers.get('User-Agent')
        print(f"  - Agent {i+1}: {agent[:60]}...")
        seen_agents.add(agent)
    
    print(f"\n✅ Total unique user agents: {len(seen_agents)}")

if __name__ == "__main__":
    test_user_agent_rotation()