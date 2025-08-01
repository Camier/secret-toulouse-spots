#!/usr/bin/env python3
"""
Unified Reddit scraper that combines functionality from all Reddit scrapers
Supports PRAW (authenticated), MCP tool, and basic modes
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from base_scraper import BaseScraper
from nlp_location_extractor import FrenchLocationExtractor

# Try to import praw for authenticated mode
try:
    import praw
    HAS_PRAW = True
except ImportError:
    HAS_PRAW = False


class UnifiedRedditScraper(BaseScraper):
    """Unified Reddit scraper with multiple operation modes"""
    
    # Subreddits to search
    SUBREDDITS = [
        "toulouse",
        "ToulouseCity", 
        "HauteGaronne",
        "Occitanie",
        "france",
        "FranceDetendue",
        "randonnee",
        "campingsauvage",
        "urbexfrance",
        "VoyageFrance",
    ]
    
    # Keywords indicating outdoor/secret spots
    OUTDOOR_KEYWORDS = [
        # Water-related
        "baignade", "cascade", "lac", "rivière", "piscine naturelle",
        "swimming", "waterfall", "lake", "river", "gour",
        
        # Nature
        "randonnée", "rando", "sentier", "chemin", "forêt",
        "hiking", "trail", "path", "forest", "nature",
        
        # Secret/Hidden
        "secret", "caché", "cachée", "peu connu", "méconnu",
        "hidden", "abandoned", "abandonné", "insolite",
        
        # Activities
        "camping", "bivouac", "escalade", "vtt", "kayak",
        "pêche", "photo", "spot photo", "point de vue",
        
        # Specific to region
        "pyrénées", "ariège", "gers", "tarn", "garonne",
    ]
    
    # Patterns for extracting coordinates
    COORD_PATTERNS = [
        r"(\d+\.\d+)[,\s]+(-?\d+\.\d+)",  # Decimal
        r"(\d+)°(\d+)'([\d.]+)\"[NS],?\s*(\d+)°(\d+)'([\d.]+)\"[EW]",  # DMS
        r"lat(?:itude)?[:\s]+(\d+\.\d+).*?lon(?:gitude)?[:\s]+(-?\d+\.\d+)",  # Named
    ]
    
    def __init__(self,
                 mode: str = "basic",
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 user_agent: str = "SecretSpotsScraper/1.0"):
        """
        Initialize scraper with specified mode
        
        Args:
            mode: "basic" (no auth), "praw" (with auth), or "mcp" (using MCP tool)
            client_id: Reddit app client ID for PRAW mode
            client_secret: Reddit app client secret for PRAW mode  
            user_agent: User agent string for Reddit API
        """
        super().__init__("reddit")
        self.mode = mode
        self.reddit = None
        self.nlp_extractor = FrenchLocationExtractor()
        
        # Setup for PRAW mode
        if mode == "praw":
            if not HAS_PRAW:
                self.logger.error("praw not installed. Install with: pip install praw")
                self.mode = "basic"
            elif client_id and client_secret:
                self._setup_praw_client(client_id, client_secret, user_agent)
            else:
                self.logger.warning("No credentials provided, falling back to basic mode")
                self.mode = "basic"
                
    def _setup_praw_client(self, client_id: str, client_secret: str, user_agent: str):
        """Setup authenticated Reddit client"""
        try:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                check_for_async=False
            )
            # Verify authentication worked
            self.reddit.user.me()  # Will raise if not authenticated
            self.logger.info("Successfully initialized and authenticated Reddit client")
        except Exception as e:
            self.logger.error(f"Failed to initialize Reddit: {e}")
            self.mode = "basic"
            
    def scrape(self, **kwargs) -> List[Dict]:
        """Main scraping method"""
        limit = kwargs.get('limit', 100)
        subreddits = kwargs.get('subreddits', self.SUBREDDITS)
        
        # Handle different parameter names
        if 'posts_per_sub' in kwargs:
            limit = kwargs['posts_per_sub']
        
        if self.mode == "praw" and self.reddit:
            return self._scrape_praw(subreddits, limit)
        elif self.mode == "mcp":
            return self._scrape_mcp(subreddits, limit)
        else:
            return self._scrape_basic(subreddits, limit)
            
    def _scrape_basic(self, subreddits: List[str], limit: int) -> List[Dict]:
        """Basic scraping (simulated for demo)"""
        self.logger.info("Running basic Reddit scraper (limited functionality)")
        self.logger.warning("For full functionality, use PRAW or MCP mode")
        
        # Return empty list as we can't actually scrape without auth
        return []
        
    def _scrape_praw(self, subreddits: List[str], limit: int) -> List[Dict]:
        """Scrape using PRAW (authenticated)"""
        self.logger.info("Running PRAW Reddit scraper")
        spots = []
        
        for subreddit_name in subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Validate subreddit exists
                try:
                    subreddit.id  # This will fail if subreddit doesn't exist
                except Exception:
                    self.logger.warning(f"Subreddit r/{subreddit_name} does not exist or is inaccessible")
                    continue
                
                # Search for outdoor posts
                for submission in subreddit.new(limit=limit):
                    if self._is_outdoor_post(submission):
                        extracted_spots = self._extract_spots_from_submission(submission)
                        spots.extend(extracted_spots)
                        
                    self.rate_limit()
                    
            except Exception as e:
                self.logger.error(f"Error scraping r/{subreddit_name}: {e}")
                
        return spots
        
    def _scrape_mcp(self, subreddits: List[str], limit: int) -> List[Dict]:
        """Scrape using MCP Reddit tool"""
        self.logger.info("Running MCP Reddit scraper")
        spots = []
        
        # Note: This would use the MCP Reddit tool
        # For now, returning empty as it requires MCP integration
        self.logger.warning("MCP mode requires Claude Code MCP integration")
        return []
        
    def _is_outdoor_post(self, submission) -> bool:
        """Check if a submission is about outdoor/secret spots"""
        text = f"{submission.title} {submission.selftext}".lower()
        
        # Check for outdoor keywords
        return any(keyword in text for keyword in self.OUTDOOR_KEYWORDS)
        
    def _extract_spots_from_submission(self, submission) -> List[Dict]:
        """Extract spots from a Reddit submission"""
        spots = []
        full_text = f"{submission.title}\n\n{submission.selftext}"
        
        # Extract locations using NLP
        location_results = self.nlp_extractor.extract_locations(full_text)
        locations = [loc['name'] for loc in location_results if loc.get('name')]
        
        # Extract coordinates using enhanced extractor from base class
        coords = self.extract_coordinates(full_text)
        
        # Check comments for additional info
        submission.comments.replace_more(limit=0)
        for comment in submission.comments.list()[:10]:  # Limit to top 10 comments
            if hasattr(comment, 'body'):
                comment_locations = self.nlp_extractor.extract_locations(comment.body)
                locations.extend([loc['name'] for loc in comment_locations if loc.get('name')])
                comment_coords = self.extract_coordinates(comment.body)
                if comment_coords and not coords:
                    coords = comment_coords
                    
        # Create spots from extracted data
        if locations:
            for location in locations[:3]:  # Max 3 spots per post
                spot = {
                    "source": f"reddit:{submission.subreddit.display_name}",
                    "source_url": f"https://reddit.com{submission.permalink}",
                    "raw_text": full_text[:1000],  # Limit text length
                    "extracted_name": location,
                    "latitude": coords[0] if coords else None,
                    "longitude": coords[1] if coords else None,
                    "location_type": self._guess_location_type(full_text),
                    "activities": self._extract_activities(full_text),
                    "is_hidden": 1 if self.is_secret_spot(full_text) else 0,
                    "metadata": {
                        "post_id": submission.id,
                        "author": str(submission.author),
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "created_utc": submission.created_utc,
                    }
                }
                spots.append(spot)
                
        # If no locations but has coordinates, create a generic spot
        elif coords:
            spot = {
                "source": f"reddit:{submission.subreddit.display_name}",
                "source_url": f"https://reddit.com{submission.permalink}",
                "raw_text": full_text[:1000],
                "extracted_name": f"Spot from r/{submission.subreddit.display_name}",
                "latitude": coords[0],
                "longitude": coords[1],
                "location_type": self._guess_location_type(full_text),
                "activities": self._extract_activities(full_text),
                "is_hidden": 1 if self.is_secret_spot(full_text) else 0,
                "metadata": {
                    "post_id": submission.id,
                    "author": str(submission.author),
                    "score": submission.score,
                }
            }
            spots.append(spot)
            
        return spots
        
        
    def _validate_toulouse_coords(self, lat: float, lon: float) -> bool:
        """Validate coordinates are in Toulouse region"""
        return 42.5 <= lat <= 44.5 and -1.0 <= lon <= 3.0
        
    def _guess_location_type(self, text: str) -> str:
        """Guess the type of location from text"""
        text_lower = text.lower()
        
        type_keywords = {
            "water": ["cascade", "lac", "rivière", "baignade", "piscine", "gour"],
            "cave": ["grotte", "caverne", "gouffre", "spéléo"],
            "ruins": ["château", "ruine", "abandonné", "urbex"],
            "viewpoint": ["vue", "panorama", "belvédère", "sommet"],
            "forest": ["forêt", "bois", "sentier", "chemin"],
        }
        
        for loc_type, keywords in type_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return loc_type
                
        return "unknown"
        
    def _extract_activities(self, text: str) -> str:
        """Extract activities from text"""
        text_lower = text.lower()
        found_activities = []
        
        activity_keywords = {
            "baignade": ["baignade", "nager", "swimming", "se baigner"],
            "randonnée": ["randonnée", "rando", "hiking", "marche"],
            "escalade": ["escalade", "grimpe", "climbing"],
            "vtt": ["vtt", "vélo", "bike", "cycling"],
            "camping": ["camping", "bivouac", "camper"],
            "photo": ["photo", "photographe", "instagram"],
            "pêche": ["pêche", "pêcher", "fishing"],
            "kayak": ["kayak", "canoë", "paddle"],
        }
        
        for activity, keywords in activity_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                found_activities.append(activity)
                
        return ", ".join(found_activities)


def main():
    """Example usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified Reddit Scraper")
    parser.add_argument("--mode", choices=["basic", "praw", "mcp"],
                        default="basic", help="Scraping mode")
    parser.add_argument("--client-id", help="Reddit client ID (praw mode)")
    parser.add_argument("--client-secret", help="Reddit client secret (praw mode)")
    parser.add_argument("--limit", type=int, default=100,
                        help="Number of posts to check per subreddit")
    parser.add_argument("--subreddits", nargs="+", 
                        help="Specific subreddits to scrape")
    
    args = parser.parse_args()
    
    # Create scraper
    scraper = UnifiedRedditScraper(
        mode=args.mode,
        client_id=args.client_id,
        client_secret=args.client_secret
    )
    
    # Run scraper
    scraper.run(limit=args.limit, subreddits=args.subreddits)


if __name__ == "__main__":
    main()