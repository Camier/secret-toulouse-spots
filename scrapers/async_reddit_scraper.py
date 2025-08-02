#!/usr/bin/env python3
"""
Async Reddit scraper using asyncpraw
High-performance concurrent scraping
"""

import asyncio
import logging
from typing import Dict, List
from datetime import datetime

try:
    import asyncpraw
    HAS_ASYNCPRAW = True
except ImportError:
    HAS_ASYNCPRAW = False
    logging.warning("asyncpraw not installed, using aiohttp fallback")

from .async_base_scraper import AsyncBaseScraper


class AsyncRedditScraper(AsyncBaseScraper):
    """Async Reddit scraper for high-performance data collection"""
    
    def __init__(self):
        super().__init__("reddit")
        self.subreddits = [
            "toulouse", "Toulouse", "hautegaronne", "Occitanie",
            "randonee", "camping", "urbex", "france"
        ]
        self.search_terms = [
            "spot secret", "endroit caché", "lieu abandonné",
            "baignade sauvage", "spot baignade", "cascade",
            "point de vue", "randonnée", "urbex toulouse"
        ]
        
    async def search_subreddit_async(self, subreddit: str, query: str) -> List[Dict]:
        """Search a subreddit for spots using Reddit JSON API"""
        spots = []
        
        # Reddit JSON API endpoint
        search_url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {
            'q': query,
            'restrict_sr': 'on',
            'sort': 'relevance',
            'limit': 100,
            't': 'all'  # All time
        }
        
        # Fetch search results
        content = await self.fetch_with_retry(search_url, params=params)
        if not content:
            return spots
            
        try:
            import json
            data = json.loads(content)
            
            # Process posts
            for post in data.get('data', {}).get('children', []):
                post_data = post.get('data', {})
                
                # Combine title and selftext
                text = f"{post_data.get('title', '')} {post_data.get('selftext', '')}"
                
                # Check if it's about a secret spot
                if self.is_secret_spot(text) or self.has_location_keywords(text):
                    # Extract coordinates
                    coords = self.extract_coordinates(text)
                    
                    spot = {
                        'source': 'reddit',
                        'source_url': f"https://reddit.com{post_data.get('permalink', '')}",
                        'raw_text': text[:1000],  # Limit text length
                        'extracted_name': self.extract_spot_name(text),
                        'activities': self.extract_activities(text),
                        'is_hidden': 1 if self.is_secret_spot(text) else 0,
                        'metadata': {
                            'subreddit': subreddit,
                            'author': post_data.get('author'),
                            'score': post_data.get('score', 0),
                            'num_comments': post_data.get('num_comments', 0),
                            'created_utc': post_data.get('created_utc')
                        }
                    }
                    
                    if coords:
                        spot['latitude'], spot['longitude'] = coords
                        
                    spots.append(spot)
                    
        except Exception as e:
            self.logger.error(f"Error parsing Reddit data: {e}")
            
        return spots
        
    async def fetch_comments_async(self, post_url: str) -> List[str]:
        """Fetch comments from a post for additional spot info"""
        # Add .json to get JSON response
        json_url = post_url.rstrip('/') + '.json'
        
        content = await self.fetch_with_retry(json_url)
        if not content:
            return []
            
        comments_text = []
        try:
            import json
            data = json.loads(content)
            
            # Comments are in the second element
            if len(data) > 1:
                comments_data = data[1].get('data', {}).get('children', [])
                
                for comment in comments_data[:20]:  # Limit to 20 comments
                    comment_body = comment.get('data', {}).get('body', '')
                    if comment_body and len(comment_body) > 50:
                        comments_text.append(comment_body)
                        
        except Exception as e:
            self.logger.error(f"Error parsing comments: {e}")
            
        return comments_text
        
    def has_location_keywords(self, text: str) -> bool:
        """Check if text contains location-related keywords"""
        keywords = [
            "coordonnées", "coordinates", "GPS", "latitude", "longitude",
            "comment y aller", "accès", "itinéraire", "directions",
            "près de", "proche de", "à côté de", "baignade", "cascade",
            "randonnée", "sentier", "chemin"
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)
        
    def extract_spot_name(self, text: str) -> str:
        """Extract potential spot name from text"""
        # Look for patterns like "Cascade de ...", "Lac de ...", etc.
        import re
        
        patterns = [
            r"(Cascade\s+de\s+[\w\s]+)",
            r"(Lac\s+de\s+[\w\s]+)",
            r"(Source\s+de\s+[\w\s]+)",
            r"(Grotte\s+de\s+[\w\s]+)",
            r"(Château\s+de\s+[\w\s]+)",
            r"(Point\s+de\s+vue\s+[\w\s]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
                
        # Fallback: try to extract from title
        if ":" in text:
            parts = text.split(":", 1)
            if len(parts[0]) < 50:
                return parts[0].strip()
                
        return None
        
    def extract_activities(self, text: str) -> str:
        """Extract activities from text"""
        activities = []
        text_lower = text.lower()
        
        activity_keywords = {
            'swimming': ['baignade', 'nager', 'swimming', 'piscine naturelle'],
            'hiking': ['randonnée', 'rando', 'hiking', 'sentier', 'marche'],
            'climbing': ['escalade', 'climbing', 'grimpe'],
            'urbex': ['urbex', 'abandonné', 'exploration urbaine'],
            'picnic': ['pique-nique', 'picnic'],
            'photography': ['photo', 'photographie', 'photography'],
            'camping': ['camping', 'bivouac', 'camper']
        }
        
        for activity, keywords in activity_keywords.items():
            if any(kw in text_lower for kw in keywords):
                activities.append(activity)
                
        return ', '.join(activities)
        
    async def scrape(self, limit_per_search: int = 50) -> List[Dict]:
        """Main async scraping method"""
        all_spots = []
        
        # Create tasks for all subreddit/search term combinations
        tasks = []
        for subreddit in self.subreddits:
            for search_term in self.search_terms:
                self.logger.info(f"Searching r/{subreddit} for '{search_term}'")
                task = self.search_subreddit_async(subreddit, search_term)
                tasks.append(task)
                
        # Execute all searches concurrently
        results = await asyncio.gather(*tasks)
        
        # Flatten results
        for spots in results:
            all_spots.extend(spots)
            
        # Remove duplicates based on URL
        unique_spots = {}
        for spot in all_spots:
            url = spot['source_url']
            if url not in unique_spots:
                unique_spots[url] = spot
                
        final_spots = list(unique_spots.values())
        self.logger.info(f"Found {len(final_spots)} unique spots from Reddit")
        
        # Fetch comments for spots with coordinates (limited to 10)
        spots_with_coords = [s for s in final_spots if 'latitude' in s][:10]
        
        if spots_with_coords:
            self.logger.info(f"Fetching comments for {len(spots_with_coords)} posts...")
            
            comment_tasks = [
                self.fetch_comments_async(spot['source_url'])
                for spot in spots_with_coords
            ]
            
            comments_results = await asyncio.gather(*comment_tasks)
            
            # Check comments for additional coordinates
            for spot, comments in zip(spots_with_coords, comments_results):
                for comment in comments:
                    coords = self.extract_coordinates(comment)
                    if coords and 'latitude' not in spot:
                        spot['latitude'], spot['longitude'] = coords
                        spot['raw_text'] += f"\n\nComment: {comment[:200]}..."
                        break
                        
        return final_spots


# Example usage
async def main():
    """Example async Reddit scraping"""
    scraper = AsyncRedditScraper()
    
    # Run the scraper
    saved = await scraper.run()
    print(f"Async Reddit scraper saved {saved} spots")
    

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    asyncio.run(main())