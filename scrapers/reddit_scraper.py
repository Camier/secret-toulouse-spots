#!/usr/bin/env python3
"""Reddit scraper for French outdoor hidden spots"""

import praw
import sqlite3
from datetime import datetime
import re
from typing import List, Dict, Optional
from math import radians, cos, sin, asin, sqrt

class RedditOutdoorScraper:
    """Scrape Reddit for French outdoor locations"""
    
    def __init__(self):
        self.db_path = "hidden_spots.db"
        
        # Toulouse coordinates for filtering
        self.toulouse_lat = 43.6047
        self.toulouse_lng = 1.4442
        self.search_radius_km = 200
        
        # Reddit instance (read-only mode for public data)
        self.reddit = praw.Reddit(
            client_id="YOUR_CLIENT_ID",
            client_secret="YOUR_CLIENT_SECRET",
            user_agent="FrenchOutdoorScraper/1.0"
        )
        
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
        
        # Search queries
        self.search_queries = [
            # Water spots
            'baignade sauvage',
            'cascade cachée',
            'lac secret',
            'piscine naturelle',
            # Hiking
            'randonnée secrète',
            'spot bivouac',
            'refuge caché',
            # Urbex
            'urbex toulouse',
            'lieu abandonné',
            'exploration urbaine',
            # Caves
            'grotte secrète',
            'spéléologie',
            'gouffre',
            # Regional
            'toulouse nature',
            'occitanie caché',
            'ariège secret',
            'lot tourisme'
        ]
        
        # Location patterns
        self.location_patterns = [
            # Departments
            r'\b(haute[- ]?garonne|ariège|tarn|lot|gers|aude|aveyron)\b',
            # Cities/towns
            r'\b(toulouse|albi|montauban|cahors|rodez|carcassonne|foix)\b',
            # Geographic features
            r'\b(pyrénées|montagne noire|causses|gorges|vallée)\b',
            # Specific locations
            r'\b(lac de [a-zàâäéèêëïîôùûç\- ]+|cascade de [a-zàâäéèêëïîôùûç\- ]+|gorges de [a-zàâäéèêëïîôùûç\- ]+)\b',
            # GPS coordinates
            r'(\d{1,2}[.,]\d+)[°\s]*[NS]?\s*[,/]\s*(\d{1,2}[.,]\d+)[°\s]*[EW]?'
        ]
        
        self.location_patterns = [re.compile(p, re.IGNORECASE) for p in self.location_patterns]
    
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
                        if 41 < lat < 46 and -2 < lng < 5:  # Rough France bounds
                            locations.append({
                                'type': 'coordinates',
                                'lat': lat,
                                'lng': lng
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
        keywords = [
            'randonnée', 'baignade', 'cascade', 'lac', 'grotte',
            'bivouac', 'camping', 'escalade', 'vtt', 'kayak',
            'urbex', 'abandonné', 'exploration', 'nature',
            'spot', 'secret', 'caché', 'sauvage', 'hors des sentiers'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)
    
    def scrape_subreddit(self, subreddit_name: str, limit: int = 100) -> List[Dict]:
        """Scrape a specific subreddit"""
        print(f"\n🔍 Scraping r/{subreddit_name}...")
        posts_data = []
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Search for each query
            for query in self.search_queries[:5]:  # Limit queries
                print(f"   Searching: {query}")
                
                try:
                    # Search posts
                    for submission in subreddit.search(query, limit=limit//len(self.search_queries)):
                        # Check if outdoor related
                        full_text = f"{submission.title} {submission.selftext}"
                        
                        if not self.is_outdoor_post(full_text):
                            continue
                        
                        # Extract locations
                        locations = self.extract_locations(full_text)
                        
                        if locations:
                            post_data = {
                                'subreddit': subreddit_name,
                                'post_id': submission.id,
                                'title': submission.title,
                                'text': submission.selftext[:1000],
                                'author': str(submission.author),
                                'created_utc': submission.created_utc,
                                'url': f"https://reddit.com{submission.permalink}",
                                'score': submission.score,
                                'locations': locations
                            }
                            posts_data.append(post_data)
                            print(f"   ✓ Found: {submission.title[:50]}...")
                        
                except Exception as e:
                    print(f"   ⚠️ Search error: {e}")
            
            # Also get hot posts
            print(f"   Checking hot posts...")
            for submission in subreddit.hot(limit=25):
                full_text = f"{submission.title} {submission.selftext}"
                
                if self.is_outdoor_post(full_text):
                    locations = self.extract_locations(full_text)
                    if locations:
                        post_data = {
                            'subreddit': subreddit_name,
                            'post_id': submission.id,
                            'title': submission.title,
                            'text': submission.selftext[:1000],
                            'author': str(submission.author),
                            'created_utc': submission.created_utc,
                            'url': f"https://reddit.com{submission.permalink}",
                            'score': submission.score,
                            'locations': locations
                        }
                        if post_data not in posts_data:
                            posts_data.append(post_data)
                            
        except Exception as e:
            print(f"   ❌ Error accessing r/{subreddit_name}: {e}")
        
        return posts_data
    
    def save_to_database(self, posts: List[Dict]):
        """Save Reddit posts to database"""
        if not posts:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved = 0
        for post in posts:
            try:
                # Save each location mention
                for loc in post['locations']:
                    location_name = loc.get('name', 'Unknown')
                    lat = loc.get('lat')
                    lng = loc.get('lng')
                    
                    # Determine if it's a hidden spot based on title/text
                    is_hidden = any(word in post['title'].lower() + post['text'].lower() 
                                  for word in ['secret', 'caché', 'peu connu', 'sauvage'])
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO scraped_locations
                        (source, source_url, raw_text, extracted_name,
                         latitude, longitude, is_hidden, scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        'reddit',
                        post['url'],
                        f"{post['title']}\n{post['text']}",
                        location_name,
                        lat,
                        lng,
                        1 if is_hidden else 0,
                        datetime.now().isoformat()
                    ))
                    
                    if cursor.rowcount > 0:
                        saved += 1
                
            except Exception as e:
                print(f"   Error saving post: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"   💾 Saved {saved} location mentions")
    
    def run_full_scrape(self):
        """Scrape all target subreddits"""
        print("🔴 Starting Reddit scraping...")
        print(f"   Target subreddits: {', '.join(self.subreddits)}")
        
        all_posts = []
        
        for subreddit in self.subreddits:
            posts = self.scrape_subreddit(subreddit, limit=50)
            all_posts.extend(posts)
            self.save_to_database(posts)
        
        print(f"\n✅ Reddit scraping complete!")
        print(f"   Total posts processed: {len(all_posts)}")
        
        # Show summary
        total_locations = sum(len(p['locations']) for p in all_posts)
        print(f"   Total location mentions: {total_locations}")

# For testing without API credentials
class RedditScraperDemo(RedditOutdoorScraper):
    """Demo version that simulates Reddit data"""
    
    def __init__(self):
        super().__init__()
        # Skip Reddit API initialization
        self.reddit = None
    
    def scrape_subreddit(self, subreddit_name: str, limit: int = 100) -> List[Dict]:
        """Simulate Reddit posts with realistic data"""
        print(f"\n🔍 Demo scraping r/{subreddit_name}...")
        
        # Simulated posts for different subreddits
        demo_posts = {
            'toulouse': [
                {
                    'title': "Cascade cachée près de Saint-Antonin-Noble-Val",
                    'text': "J'ai découvert une superbe cascade peu connue à 45.1234, 1.7532. Accès par le sentier GR36, après 2km prendre à gauche.",
                    'locations': [
                        {'type': 'name', 'name': 'Saint-Antonin-Noble-Val'},
                        {'type': 'coordinates', 'lat': 45.1234, 'lng': 1.7532}
                    ]
                },
                {
                    'title': "Spot de baignade sauvage dans les Gorges de l'Aveyron",
                    'text': "Pour ceux qui cherchent un coin tranquille, il y a un endroit secret près de Bruniquel. L'eau est cristalline!",
                    'locations': [
                        {'type': 'name', 'name': 'Gorges de l\'Aveyron'},
                        {'type': 'name', 'name': 'Bruniquel'}
                    ]
                }
            ],
            'occitanie': [
                {
                    'title': "Grotte secrète en Ariège - spéléo débutant",
                    'text': "Découverte d'une petite grotte non répertoriée près de Foix. Coordonnées: 42.9656, 1.6055. Attention, matériel nécessaire!",
                    'locations': [
                        {'type': 'name', 'name': 'Ariège'},
                        {'type': 'name', 'name': 'Foix'},
                        {'type': 'coordinates', 'lat': 42.9656, 'lng': 1.6055}
                    ]
                }
            ],
            'france': [
                {
                    'title': "Urbex: Château abandonné dans le Lot",
                    'text': "Superbe château en ruine près de Cahors. Accès libre mais dangereux. GPS: 44.4472, 1.4414",
                    'locations': [
                        {'type': 'name', 'name': 'Lot'},
                        {'type': 'name', 'name': 'Cahors'},
                        {'type': 'coordinates', 'lat': 44.4472, 'lng': 1.4414}
                    ]
                }
            ]
        }
        
        posts_data = []
        if subreddit_name in demo_posts:
            for i, post_template in enumerate(demo_posts[subreddit_name]):
                post_data = {
                    'subreddit': subreddit_name,
                    'post_id': f'demo_{subreddit_name}_{i}',
                    'title': post_template['title'],
                    'text': post_template['text'],
                    'author': 'demo_user',
                    'created_utc': datetime.now().timestamp(),
                    'url': f"https://reddit.com/r/{subreddit_name}/demo_{i}",
                    'score': 42,
                    'locations': post_template['locations']
                }
                posts_data.append(post_data)
                print(f"   ✓ Found: {post_data['title']}")
        
        return posts_data

if __name__ == "__main__":
    # Use demo version for testing
    print("🔴 Reddit Scraper (Demo Mode)")
    print("   Note: Using simulated data. Set up Reddit API credentials for real data.")
    
    scraper = RedditScraperDemo()
    scraper.run_full_scrape()