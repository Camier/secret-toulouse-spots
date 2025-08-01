#!/usr/bin/env python3
"""
Enhanced Reddit scraper for finding secret spots around Toulouse
Searches multiple subreddits and keywords
"""

import requests
import sqlite3
import re
import json
from datetime import datetime
import time

# Subreddits to search
SUBREDDITS = [
    'toulouse',
    'france',
    'Occitanie', 
    'randonnee',
    'VoyageFrance',
    'AskFrance',
    'urbex',
    'urbanexploration'
]

# Search terms (in French and English)
SEARCH_TERMS = [
    # Water spots
    'baignade sauvage toulouse',
    'spot baignade secret',
    'cascade cachée',
    'piscine naturelle',
    'rivière baignade',
    'lac secret toulouse',
    
    # Urban exploration
    'urbex toulouse',
    'lieu abandonné toulouse',
    'batiment abandonné',
    'friche industrielle',
    
    # Nature spots
    'randonnée secrète toulouse',
    'spot photo toulouse',
    'point de vue caché',
    'grotte toulouse',
    'forêt méconnue',
    
    # General hidden places
    'endroit secret toulouse',
    'lieu méconnu toulouse',
    'spot caché toulouse',
    'coin sympa toulouse',
    'hors des sentiers battus'
]

# Regex patterns to extract coordinates
COORD_PATTERNS = [
    r'(\d{1,2}[.,]\d+)[°\s,]+(\d{1,2}[.,]\d+)',  # 43.123, 1.456
    r'(\d{2}°\d{2}\'\d{2}\"[NS])[,\s]+(\d{1,3}°\d{2}\'\d{2}\"[EW])',  # DMS format
    r'lat[:\s]+(\d{1,2}[.,]\d+).*?lon[:\s]+(\d{1,2}[.,]\d+)',  # lat: 43.123 lon: 1.456
]

# Location keywords that suggest proximity to Toulouse
LOCATION_KEYWORDS = [
    'toulouse', 'muret', 'blagnac', 'colomiers', 'tournefeuille',
    'balma', 'ramonville', 'castanet', 'portet', 'cugnaux',
    'saint-gaudens', 'albi', 'montauban', 'castres', 'pamiers',
    'foix', 'carcassonne', 'auch', 'tarbes', 'ariège', 'gers',
    'haute-garonne', 'tarn', 'aude', 'aveyron', 'lot',
    'midi-pyrénées', 'occitanie', 'pyrenees', 'pyrénées'
]

def extract_coordinates(text):
    """Extract coordinates from text"""
    for pattern in COORD_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            lat_str = match.group(1).replace(',', '.')
            lon_str = match.group(2).replace(',', '.')
            try:
                lat = float(lat_str)
                lon = float(lon_str)
                # Basic validation for France region
                if 41 < lat < 46 and -2 < lon < 5:
                    return lat, lon
            except:
                pass
    return None, None

def extract_location_info(text):
    """Extract location information from text"""
    text_lower = text.lower()
    
    # Check for location keywords
    mentioned_locations = []
    for keyword in LOCATION_KEYWORDS:
        if keyword in text_lower:
            mentioned_locations.append(keyword)
    
    # Extract potential spot names
    spot_patterns = [
        r'(?:cascade|lac|plage|grotte|pont|château|moulin|source|fontaine)\s+(?:de |du |des |d\')?([A-Z][a-zéèêëàâäôöûü\-]+(?:\s+[A-Z][a-zéèêëàâäôöûü\-]+)*)',
        r'(?:à |au |aux )?([A-Z][a-zéèêëàâäôöûü\-]+(?:\s+[A-Z][a-zéèêëàâäôöûü\-]+)*)\s+(?:caché|secret|méconnu|sauvage)',
    ]
    
    potential_names = []
    for pattern in spot_patterns:
        matches = re.findall(pattern, text)
        potential_names.extend(matches)
    
    return {
        'locations': mentioned_locations,
        'potential_names': potential_names
    }

def search_reddit():
    """Search Reddit for secret spots"""
    # Read-only mode without credentials - using JSON API
    print("📱 Searching Reddit for secret spots...")
    
    all_posts = []
    
    for subreddit in SUBREDDITS:
        print(f"  Searching r/{subreddit}...")
        
        # Search for each term
        for term in SEARCH_TERMS[:5]:  # Limit to avoid rate limiting
            try:
                # Use Reddit's JSON API (no auth required for public data)
                url = f"https://www.reddit.com/r/{subreddit}/search.json"
                params = {
                    'q': term,
                    'restrict_sr': 'on',
                    'sort': 'relevance',
                    'limit': 25
                }
                headers = {'User-Agent': 'SecretSpotsBot/1.0 (by /u/your_username)'}
                
                response = requests.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    posts = data.get('data', {}).get('children', [])
                    
                    for post in posts:
                        post_data = post.get('data', {})
                        
                        # Check if post mentions location keywords
                        text = f"{post_data.get('title', '')} {post_data.get('selftext', '')}"
                        if any(loc in text.lower() for loc in LOCATION_KEYWORDS):
                            all_posts.append({
                                'title': post_data.get('title', ''),
                                'text': post_data.get('selftext', ''),
                                'subreddit': post_data.get('subreddit', ''),
                                'author': post_data.get('author', ''),
                                'url': f"https://reddit.com{post_data.get('permalink', '')}",
                                'created_utc': post_data.get('created_utc', 0)
                            })
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                print(f"    Error searching {term} in r/{subreddit}: {e}")
                continue
    
    # Remove duplicates based on URL
    unique_posts = []
    seen_urls = set()
    for post in all_posts:
        if post['url'] not in seen_urls:
            seen_urls.add(post['url'])
            unique_posts.append(post)
    
    print(f"  Found {len(unique_posts)} unique posts mentioning locations")
    return unique_posts

def process_reddit_data(posts):
    """Process Reddit posts and extract spot information"""
    spots = []
    
    for post in posts:
        # Combine title and text
        full_text = f"{post['title']} {post['text']}"
        
        # Extract coordinates
        lat, lon = extract_coordinates(full_text)
        
        # Extract location info
        location_info = extract_location_info(full_text)
        
        # Determine spot name
        if location_info['potential_names']:
            spot_name = location_info['potential_names'][0]
        else:
            spot_name = post['title'][:50]
        
        # Determine if it's hidden/secret
        is_hidden = any(word in full_text.lower() for word in [
            'secret', 'caché', 'méconnu', 'peu connu', 'sauvage', 'abandonné'
        ])
        
        spot = {
            'source': f"reddit_{post.get('subreddit', 'unknown')}",
            'source_url': post.get('url', ''),
            'raw_text': full_text,
            'extracted_name': spot_name,
            'latitude': lat,
            'longitude': lon,
            'location_type': 'reddit_mention',
            'activities': extract_activities(full_text),
            'is_hidden': 1 if is_hidden else 0,
            'discovery_snippet': post.get('text', '')[:200],
            'mentioned_locations': ','.join(location_info['locations'])
        }
        
        spots.append(spot)
    
    return spots

def extract_activities(text):
    """Extract activities from text"""
    activities = []
    text_lower = text.lower()
    
    activity_keywords = {
        'baignade': ['baignade', 'nager', 'piscine', 'plage'],
        'randonnée': ['randonnée', 'rando', 'marche', 'sentier', 'trek'],
        'escalade': ['escalade', 'grimpe', 'varappe'],
        'VTT': ['vtt', 'vélo', 'bike', 'cyclisme'],
        'photo': ['photo', 'photographe', 'vue', 'panorama'],
        'pique-nique': ['pique-nique', 'picnic', 'bbq', 'barbecue'],
        'urbex': ['urbex', 'abandonné', 'exploration urbaine'],
        'spéléologie': ['spéléo', 'grotte', 'caverne', 'gouffre'],
        'pêche': ['pêche', 'poisson', 'truite'],
        'kayak': ['kayak', 'canoë', 'paddle', 'raft']
    }
    
    for activity, keywords in activity_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            activities.append(activity)
    
    return ', '.join(activities) if activities else None

def save_to_database(spots):
    """Save spots to database"""
    conn = sqlite3.connect('hidden_spots.db')
    cursor = conn.cursor()
    
    saved_count = 0
    for spot in spots:
        # Check if already exists
        cursor.execute('''
            SELECT id FROM spots 
            WHERE source = ? AND extracted_name = ?
        ''', (spot['source'], spot['extracted_name']))
        
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO spots (
                    source, source_url, raw_text, extracted_name,
                    latitude, longitude, location_type, activities,
                    is_hidden, discovery_snippet, scraped_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                spot['source'],
                spot['source_url'],
                spot['raw_text'],
                spot['extracted_name'],
                spot['latitude'],
                spot['longitude'],
                spot['location_type'],
                spot['activities'],
                spot['is_hidden'],
                spot['discovery_snippet'],
                datetime.now().isoformat(),
                json.dumps({'mentioned_locations': spot.get('mentioned_locations', '')})
            ))
            saved_count += 1
    
    conn.commit()
    conn.close()
    
    return saved_count

def main():
    print("🔍 Starting enhanced Reddit scraper...")
    
    # Search Reddit
    posts = search_reddit()
    print(f"📝 Found {len(posts)} posts to process")
    
    # Process posts
    spots = process_reddit_data(posts)
    print(f"📍 Extracted {len(spots)} potential spots")
    
    # Save to database
    saved = save_to_database(spots)
    print(f"💾 Saved {saved} new spots to database")
    
    # Show summary
    with_coords = len([s for s in spots if s['latitude'] and s['longitude']])
    hidden = len([s for s in spots if s['is_hidden']])
    
    print(f"\n✅ Summary:")
    print(f"   Posts processed: {len(posts)}")
    print(f"   Spots extracted: {len(spots)}")
    print(f"   With coordinates: {with_coords}")
    print(f"   Hidden/secret: {hidden}")
    print(f"   New spots saved: {saved}")

if __name__ == "__main__":
    main()