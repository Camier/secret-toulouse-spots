#!/usr/bin/env python3
"""Reddit MCP scraper for French outdoor hidden spots"""

import sqlite3
from datetime import datetime
import re
from typing import List, Dict, Optional
from math import radians, cos, sin, asin, sqrt

class RedditMCPScraper:
    """Scrape Reddit using MCP integration"""
    
    def __init__(self):
        self.db_path = "hidden_spots.db"
        
        # Toulouse coordinates for filtering
        self.toulouse_lat = 43.6047
        self.toulouse_lng = 1.4442
        self.search_radius_km = 200
        
        # French outdoor subreddits
        self.subreddits = [
            'france',
            'toulouse', 
            'occitanie',
            'randonee',
            'VoyageFrance',
            'AskFrance',
            'pyrenees',
            'midi_pyrenees'
        ]
        
        # Search queries for outdoor spots
        self.search_queries = [
            # Water spots
            'baignade sauvage toulouse',
            'cascade cachée occitanie',
            'lac secret midi pyrénées',
            'piscine naturelle ariège',
            # Hiking
            'randonnée secrète toulouse',
            'spot bivouac pyrénées',
            'refuge caché occitanie',
            # Urbex
            'urbex toulouse',
            'lieu abandonné occitanie',
            'château abandonné midi pyrénées',
            # Caves
            'grotte secrète ariège',
            'spéléologie toulouse',
            'gouffre occitanie',
            # General
            'spot secret toulouse',
            'endroit caché occitanie'
        ]
        
        # Location patterns
        self.location_patterns = [
            # Departments
            r'\b(haute[- ]?garonne|ariège|tarn|lot|gers|aude|aveyron|tarn[- ]?et[- ]?garonne)\b',
            # Cities/towns
            r'\b(toulouse|albi|montauban|cahors|rodez|carcassonne|foix|auch|tarbes)\b',
            # Geographic features
            r'\b(pyrénées|montagne noire|causses|gorges|vallée)\b',
            # Specific locations
            r'\b(lac de [a-zàâäéèêëïîôùûç\- ]+|cascade de [a-zàâäéèêëïîôùûç\- ]+|gorges de [a-zàâäéèêëïîôùûç\- ]+)\b',
            # GPS coordinates
            r'(\d{1,2}[.,]\d+)[°\s]*[NS]?\s*[,/]\s*(\d{1,2}[.,]\d+)[°\s]*[EW]?'
        ]
        
        self.location_patterns = [re.compile(p, re.IGNORECASE) for p in self.location_patterns]
        
        # Keywords for identifying outdoor posts
        self.outdoor_keywords = [
            'randonnée', 'baignade', 'cascade', 'lac', 'grotte',
            'bivouac', 'camping', 'escalade', 'vtt', 'kayak',
            'urbex', 'abandonné', 'exploration', 'nature',
            'spot', 'secret', 'caché', 'sauvage', 'hors des sentiers',
            'piscine naturelle', 'source', 'gouffre', 'spéléo',
            'ruine', 'château', 'moulin', 'pont'
        ]
        
        # Hidden spot indicators
        self.hidden_keywords = [
            'secret', 'caché', 'peu connu', 'sauvage', 'préservé',
            'hors des sentiers', 'méconnu', 'confidentiel', 'insolite',
            'abandonné', 'désaffecté', 'oublié', 'inexploré'
        ]
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points on Earth"""
        R = 6371  # Earth's radius in kilometers
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        return R * c
    
    def extract_locations(self, text: str) -> List[Dict]:
        """Extract location mentions from text"""
        locations = []
        
        for pattern in self.location_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):  # GPS coordinates
                    try:
                        lat = float(match[0].replace(',', '.'))
                        lng = float(match[1].replace(',', '.'))
                        # Check if coordinates are in France region
                        if 41 < lat < 51 and -5 < lng < 10:
                            # Check if within search radius
                            distance = self.haversine_distance(
                                self.toulouse_lat, self.toulouse_lng, lat, lng
                            )
                            if distance <= self.search_radius_km:
                                locations.append({
                                    'type': 'coordinates',
                                    'lat': lat,
                                    'lng': lng,
                                    'distance_km': distance
                                })
                    except:
                        pass
                else:
                    locations.append({
                        'type': 'name',
                        'name': match.strip()
                    })
        
        return locations
    
    def is_outdoor_post(self, text: str) -> bool:
        """Check if post is about outdoor activities"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.outdoor_keywords)
    
    def is_hidden_spot(self, text: str) -> bool:
        """Check if post mentions a hidden/secret spot"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.hidden_keywords)
    
    def determine_activity_type(self, text: str) -> str:
        """Determine the type of outdoor activity"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['cascade', 'lac', 'baignade', 'piscine naturelle', 'rivière']):
            return 'water'
        elif any(word in text_lower for word in ['grotte', 'gouffre', 'spéléo', 'caverne']):
            return 'cave'
        elif any(word in text_lower for word in ['urbex', 'abandonné', 'ruine', 'château', 'friche']):
            return 'urbex'
        elif any(word in text_lower for word in ['randonnée', 'bivouac', 'refuge', 'sentier', 'gr']):
            return 'hiking'
        else:
            return 'general'
    
    def save_to_database(self, posts: List[Dict]):
        """Save Reddit posts to database"""
        if not posts:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved = 0
        for post in posts:
            try:
                # Process each location
                for loc in post['locations']:
                    location_name = loc.get('name', f"GPS: {loc.get('lat')}, {loc.get('lng')}")
                    lat = loc.get('lat')
                    lng = loc.get('lng')
                    
                    # Skip if no valid location
                    if not location_name and not (lat and lng):
                        continue
                    
                    # Prepare metadata
                    metadata = {
                        'subreddit': post['subreddit'],
                        'post_id': post['post_id'],
                        'score': post.get('score', 0),
                        'author': post.get('author', 'unknown'),
                        'distance_km': loc.get('distance_km')
                    }
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO scraped_locations
                        (source, source_url, raw_text, extracted_name,
                         latitude, longitude, location_type, activities,
                         is_hidden, scraped_at, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        'reddit',
                        post['url'],
                        post['full_text'][:1000],  # Truncate long text
                        location_name,
                        lat,
                        lng,
                        'outdoor_spot',
                        post.get('activity_type', 'general'),
                        1 if post.get('is_hidden') else 0,
                        datetime.now().isoformat(),
                        str(metadata)
                    ))
                    
                    if cursor.rowcount > 0:
                        saved += 1
                
            except Exception as e:
                print(f"   Error saving post: {e}")
        
        conn.commit()
        conn.close()
        
        return saved
    
    def process_search_results(self, results: List[Dict]) -> List[Dict]:
        """Process search results into our format"""
        processed = []
        
        for result in results:
            # Get full text
            full_text = f"{result.get('title', '')} {result.get('selftext', '')}"
            
            # Skip if not outdoor related
            if not self.is_outdoor_post(full_text):
                continue
            
            # Extract locations
            locations = self.extract_locations(full_text)
            if not locations:
                continue
            
            # Build processed post
            post_data = {
                'subreddit': result.get('subreddit', '').replace('r/', ''),
                'post_id': result.get('id', ''),
                'title': result.get('title', ''),
                'full_text': full_text,
                'author': result.get('author', 'unknown'),
                'url': f"https://reddit.com{result.get('permalink', '')}",
                'score': result.get('score', 0),
                'locations': locations,
                'is_hidden': self.is_hidden_spot(full_text),
                'activity_type': self.determine_activity_type(full_text)
            }
            
            processed.append(post_data)
            
        return processed
    
    def run_scraping(self):
        """Main scraping function using MCP"""
        print("🔴 Starting Reddit MCP scraping...")
        print(f"   Search radius: {self.search_radius_km}km from Toulouse")
        print(f"   Target subreddits: {', '.join(self.subreddits)}")
        
        total_posts = 0
        total_saved = 0
        
        # Note: Since we'll call this from Claude Code with MCP tools,
        # we'll return the queries and let the main script handle the MCP calls
        return {
            'queries': self.search_queries,
            'subreddits': self.subreddits,
            'process_function': self.process_search_results,
            'save_function': self.save_to_database
        }

if __name__ == "__main__":
    print("🔴 Reddit MCP Scraper")
    print("   This scraper should be run through the main_scraper_extended.py")
    print("   It will use the Reddit MCP server for actual data retrieval.")
    
    scraper = RedditMCPScraper()
    config = scraper.run_scraping()
    print(f"\n   Configured with {len(config['queries'])} search queries")
    print(f"   Ready to search {len(config['subreddits'])} subreddits")