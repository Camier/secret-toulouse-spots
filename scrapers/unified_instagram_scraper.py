#!/usr/bin/env python3
"""
Unified Instagram scraper that combines functionality from all Instagram scrapers
Supports basic, secure (with auth), and continuous modes
"""

import json
import os
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from base_scraper import BaseScraper

# Try to import instagrapi for secure mode
try:
    from instagrapi import Client
    HAS_INSTAGRAPI = True
except ImportError:
    HAS_INSTAGRAPI = False


class UnifiedInstagramScraper(BaseScraper):
    """Unified Instagram scraper with multiple operation modes"""
    
    # Hashtags with relevance weights
    HASHTAGS = {
        # High relevance (0.8-1.0)
        "toulousesecret": 0.9,
        "spotsecrettoulouse": 0.8,
        "toulousecachée": 0.8,
        "baignadesauvagetoulouse": 0.9,
        "cascadecachée": 0.9,
        "urbextoulouse": 0.8,
        "pyreneescachées": 0.9,
        
        # Medium relevance (0.5-0.8)
        "randonnéesecrète": 0.6,
        "grottetoulouse": 0.7,
        "abandonnétoulouse": 0.7,
        "viewpointtoulouse": 0.6,
        "hautegaronnesecret": 0.7,
        "occitaniesecrete": 0.7,
        "patrimoinecaché": 0.7,
        "lieuxinsolites": 0.7,
        
        # Lower relevance (0.3-0.5)
        "toulouseinsolite": 0.5,
        "igerstoulouse": 0.3,
        "visittoulouse": 0.3,
        "exploretoulouse": 0.4,
        "toulousenature": 0.5,
        "escapadetoulouse": 0.4,
    }
    
    # Location templates for simulation mode
    LOCATION_TEMPLATES = [
        {
            "type": "waterfall",
            "name_patterns": ["Cascade de {}", "Cascade secrète de {}"],
            "locations": ["Arbas", "Aspet", "Saint-Béat", "Boutx", "Luchon"],
            "activities": ["baignade", "randonnée", "photo"],
        },
        {
            "type": "cave",
            "name_patterns": ["Grotte de {}", "Gouffre de {}"],
            "locations": ["Aurignac", "Montréjeau", "Arbas", "Herran"],
            "activities": ["spéléologie", "exploration"],
        },
        {
            "type": "ruins",
            "name_patterns": ["Château abandonné de {}", "Ruines de {}"],
            "locations": ["Rieux", "Martres-Tolosane", "Carbonne"],
            "activities": ["urbex", "photo", "exploration"],
        },
        {
            "type": "natural_pool",
            "name_patterns": ["Gour de {}", "Vasque de {}"],
            "locations": ["Arbas", "Portet", "Saint-Lary"],
            "activities": ["baignade", "cliff jumping"],
        },
    ]
    
    def __init__(self, 
                 mode: str = "basic",
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 continuous_duration: int = 0):
        """
        Initialize scraper with specified mode
        
        Args:
            mode: "basic" (no auth), "secure" (with auth), or "continuous" (simulation)
            username: Instagram username for secure mode
            password: Instagram password for secure mode
            continuous_duration: Duration in seconds for continuous mode
        """
        super().__init__("instagram")
        self.mode = mode
        self.continuous_duration = continuous_duration
        self.client = None
        
        # Setup for secure mode
        if mode == "secure":
            if not HAS_INSTAGRAPI:
                self.logger.error("instagrapi not installed. Install with: pip install instagrapi")
                self.mode = "basic"
            elif username and password:
                self._setup_secure_client(username, password)
            else:
                self.logger.warning("No credentials provided, falling back to basic mode")
                self.mode = "basic"
                
    def _setup_secure_client(self, username: str, password: str):
        """Setup authenticated Instagram client"""
        try:
            self.client = Client()
            self.client.login(username, password)
            self.logger.info("Successfully logged in to Instagram")
        except Exception as e:
            self.logger.error(f"Failed to login: {e}")
            self.mode = "basic"
            
    def scrape(self, limit: int = 50) -> List[Dict]:
        """Main scraping method"""
        if self.mode == "continuous":
            return self._scrape_continuous()
        elif self.mode == "secure" and self.client:
            return self._scrape_secure(limit)
        else:
            return self._scrape_basic(limit)
            
    def _scrape_basic(self, limit: int) -> List[Dict]:
        """Basic scraping without authentication (simulated data)"""
        self.logger.info("Running basic Instagram scraper (simulated data)")
        spots = []
        
        for hashtag, weight in random.sample(list(self.HASHTAGS.items()), min(10, len(self.HASHTAGS))):
            # Simulate finding posts
            num_posts = random.randint(1, 5)
            for _ in range(num_posts):
                if len(spots) >= limit:
                    break
                    
                spot = self._generate_simulated_spot(hashtag, weight)
                if spot:
                    spots.append(spot)
                    self.rate_limit()
                    
        return spots
        
    def _scrape_secure(self, limit: int) -> List[Dict]:
        """Secure scraping with authentication"""
        self.logger.info("Running secure Instagram scraper")
        spots = []
        
        for hashtag, weight in self.HASHTAGS.items():
            if len(spots) >= limit:
                break
                
            try:
                # Get hashtag posts
                medias = self.client.hashtag_medias_recent(hashtag, amount=20)
                
                for media in medias:
                    if len(spots) >= limit:
                        break
                        
                    spot = self._process_media(media, hashtag, weight)
                    if spot:
                        spots.append(spot)
                        
                self.rate_limit()
                
            except Exception as e:
                self.logger.error(f"Error scraping #{hashtag}: {e}")
                
        return spots
        
    def _scrape_continuous(self) -> List[Dict]:
        """Continuous scraping mode (simulation)"""
        self.logger.info(f"Running continuous scraper for {self.continuous_duration}s")
        spots = []
        start_time = time.time()
        
        while time.time() - start_time < self.continuous_duration:
            # Generate a batch of spots
            batch_size = random.randint(1, 3)
            for _ in range(batch_size):
                hashtag, weight = random.choice(list(self.HASHTAGS.items()))
                spot = self._generate_simulated_spot(hashtag, weight)
                if spot:
                    spots.append(spot)
                    # Save immediately in continuous mode
                    self.save_spot(spot)
                    
            # Wait before next batch
            wait_time = random.randint(30, 120)
            self.logger.info(f"Generated {batch_size} spots, waiting {wait_time}s...")
            time.sleep(wait_time)
            
        return spots
        
    def _generate_simulated_spot(self, hashtag: str, weight: float) -> Optional[Dict]:
        """Generate a simulated Instagram spot"""
        if random.random() > weight:  # Use weight as probability
            return None
            
        template = random.choice(self.LOCATION_TEMPLATES)
        location = random.choice(template["locations"])
        
        # Generate coordinates near Toulouse
        base_lat, base_lon = 43.6047, 1.4442  # Toulouse center
        lat = base_lat + random.uniform(-0.5, 0.5)
        lon = base_lon + random.uniform(-0.5, 0.5)
        
        spot_name = random.choice(template["name_patterns"]).format(location)
        
        return {
            "source": f"instagram:#{hashtag}",
            "source_url": f"https://instagram.com/p/{self._generate_fake_id()}",
            "raw_text": self._generate_post_text(spot_name, template),
            "extracted_name": spot_name,
            "latitude": lat,
            "longitude": lon,
            "location_type": template["type"],
            "activities": ", ".join(random.sample(template["activities"], 
                                                 min(2, len(template["activities"])))),
            "is_hidden": 1 if weight > 0.7 else 0,
            "metadata": {
                "hashtag": hashtag,
                "relevance_score": weight,
                "likes": random.randint(50, 500),
                "comments": random.randint(5, 50),
            }
        }
        
    def _generate_post_text(self, spot_name: str, template: Dict) -> str:
        """Generate realistic Instagram post text"""
        texts = [
            f"🌟 Découverte du jour: {spot_name}! Un endroit magique et peu connu 🏞️",
            f"📍 {spot_name} - Mon nouveau spot secret préféré! 🤫",
            f"Qui connaît {spot_name}? Trouvé par hasard et complètement sous le charme! 💙",
            f"Weekend parfait à {spot_name} 🌿 Accessible après 30min de marche",
        ]
        
        post = random.choice(texts)
        post += f"\n\n📸 {datetime.now().strftime('%B %Y')}"
        post += f"\n🏃 Activités: {', '.join(template['activities'])}"
        
        return post
        
    def _generate_fake_id(self) -> str:
        """Generate fake Instagram post ID"""
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        return ''.join(random.choice(chars) for _ in range(11))
        
    def _process_media(self, media, hashtag: str, weight: float) -> Optional[Dict]:
        """Process Instagram media object (for secure mode)"""
        try:
            caption = media.caption_text if media.caption_text else ""
            
            # Check if it's a secret spot
            if not self.is_secret_spot(caption):
                return None
                
            location = None
            lat, lon = None, None
            
            # Extract location info
            if media.location:
                location = media.location.name
                lat = media.location.lat
                lon = media.location.lng
                
            return {
                "source": f"instagram:#{hashtag}",
                "source_url": f"https://instagram.com/p/{media.code}",
                "raw_text": caption,
                "extracted_name": location or f"Spot from #{hashtag}",
                "latitude": lat,
                "longitude": lon,
                "location_type": "unknown",
                "activities": "",
                "is_hidden": 1 if weight > 0.7 else 0,
                "metadata": {
                    "hashtag": hashtag,
                    "relevance_score": weight,
                    "likes": media.like_count,
                    "comments": media.comment_count,
                    "user": media.user.username,
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error processing media: {e}")
            return None


def main():
    """Example usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified Instagram Scraper")
    parser.add_argument("--mode", choices=["basic", "secure", "continuous"],
                        default="basic", help="Scraping mode")
    parser.add_argument("--username", help="Instagram username (secure mode)")
    parser.add_argument("--password", help="Instagram password (secure mode)")
    parser.add_argument("--duration", type=int, default=300,
                        help="Duration in seconds (continuous mode)")
    parser.add_argument("--limit", type=int, default=50,
                        help="Number of posts to scrape")
    
    args = parser.parse_args()
    
    # Create scraper
    scraper = UnifiedInstagramScraper(
        mode=args.mode,
        username=args.username,
        password=args.password,
        continuous_duration=args.duration
    )
    
    # Run scraper
    scraper.run(limit=args.limit)


if __name__ == "__main__":
    main()