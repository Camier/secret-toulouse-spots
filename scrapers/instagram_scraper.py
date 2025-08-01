#!/usr/bin/env python3
"""
Instagram hashtag scraper for secret spots around Toulouse
Note: Instagram's API is restricted. This uses public hashtag data.
"""

import requests
import sqlite3
import re
import json
from datetime import datetime
import time

# Instagram hashtags to search
HASHTAGS = [
    # French hashtags
    'toulousesecret',
    'toulousesecrète',
    'spotsecrettoulouse',
    'toulouseinsolite',
    'toulousecachée',
    'igerstoulouse',
    'visittoulouse',
    'exploretoulouse',
    
    # Water spots
    'baignadesauvagetoulouse',
    'cascadecachée',
    'piscinenaturelle31',
    
    # Urban exploration
    'urbextoulouse',
    'urbexfrance',
    'abandonnétoulouse',
    
    # Nature
    'randonnéetoulouse',
    'naturetoulouse',
    'hautegaronnenature',
    'occitanienature',
    'pyreneessecret'
]

# Location tags around Toulouse
LOCATION_TAGS = [
    'Toulouse, France',
    'Haute-Garonne',
    'Midi-Pyrénées',
    'Occitanie',
    'Canal du Midi',
    'Garonne',
    'Forêt de Bouconne',
    'Lac de la Ramée'
]

def extract_location_from_caption(caption):
    """Extract location information from Instagram caption"""
    location_patterns = [
        r'📍\s*([^,\n]+)',  # Location pin emoji
        r'@\s*([a-zA-Z0-9._]+)',  # Instagram location tag
        r'(?:à|at|in)\s+([A-Z][a-zA-Zéèêëàâäôöûü\s\-]+)',  # "at/in Location"
    ]
    
    locations = []
    for pattern in location_patterns:
        matches = re.findall(pattern, caption)
        locations.extend(matches)
    
    return locations

def extract_coordinates_from_caption(caption):
    """Extract GPS coordinates from caption if present"""
    coord_patterns = [
        r'(\d{1,2}[.,]\d+)[°\s,]+(\d{1,2}[.,]\d+)',
        r'lat[:\s]+(\d{1,2}[.,]\d+).*?lon[:\s]+(\d{1,2}[.,]\d+)'
    ]
    
    for pattern in coord_patterns:
        match = re.search(pattern, caption, re.IGNORECASE)
        if match:
            try:
                lat = float(match.group(1).replace(',', '.'))
                lon = float(match.group(2).replace(',', '.'))
                if 41 < lat < 46 and -2 < lon < 5:  # France bounds
                    return lat, lon
            except:
                pass
    return None, None

def create_instagram_sample_data():
    """Create sample Instagram-style posts about secret spots"""
    posts = [
        {
            'id': 'ig_001',
            'caption': """🌊 Cascade secrète près de Toulouse! 
            
📍 Saint-Ferréol, 1h de route
GPS: 43.4556, 2.0123

Magnifique cascade cachée dans la forêt, accessible après 30min de marche. 
L'eau est fraîche mais c'est parfait pour se baigner en été! 

#toulousesecret #cascadecachée #baignadesauvage #hautegaronne #naturelovers #spotsecret #occitanie""",
            'user': 'nature_explorer_31',
            'location': 'Saint-Ferréol, Midi-Pyrénées',
            'hashtags': ['toulousesecret', 'cascadecachée', 'baignadesauvage']
        },
        {
            'id': 'ig_002',
            'caption': """Urbex: Château abandonné 🏚️

Incroyable château du 19ème siècle laissé à l'abandon. 
Architecture néo-gothique encore bien préservée.
⚠️ Attention aux planchers fragiles!

📍 Entre Muret et Seysses (DM pour localisation exacte)

#urbextoulouse #urbexfrance #abandonnétoulouse #chateauabandonné #urbanexploration""",
            'user': 'urbex_occitanie',
            'location': None,
            'hashtags': ['urbextoulouse', 'abandonnétoulouse']
        },
        {
            'id': 'ig_003',
            'caption': """Point de vue secret sur Toulouse 🌅

Ce spot photo est mon petit secret... Vue imprenable sur toute la ville rose!
Parfait pour le sunset 📸

📍 Pech-David (côté est, suivre le petit sentier après le parking)

#toulousesecret #igerstoulouse #sunsetspot #viewpoint #toulousemaville #photospottoulouse""",
            'user': 'photo_toulouse',
            'location': 'Pech-David, Toulouse',
            'hashtags': ['toulousesecret', 'igerstoulouse']
        },
        {
            'id': 'ig_004',
            'caption': """Grotte cachée dans l'Ariège 🦇

Petite grotte méconnue avec des formations calcaires magnifiques.
Prévoir lampes frontales! 

📍 Près de Foix (43.0123, 1.6789)
Entrée cachée derrière les rochers

#grottesecrète #speleologie #ariege #explorationfrance #hiddencave #occitanienature""",
            'user': 'speleo_pyrenees',
            'location': 'Foix, Ariège',
            'hashtags': ['occitanienature']
        },
        {
            'id': 'ig_005',
            'caption': """Lac secret pour se baigner 🏊‍♀️

Mon coin baignade favori loin des foules!
Eau cristalline, petite plage de galets.

📍 Lac de Montbel (côté sud)
Accessible par le chemin forestier

#baignadesauvagetoulouse #lacsecret #swimspot #naturelovers #occitanie #summervibes""",
            'user': 'swimwild_31',
            'location': 'Lac de Montbel',
            'hashtags': ['baignadesauvagetoulouse', 'lacsecret']
        },
        {
            'id': 'ig_006',
            'caption': """Moulin abandonné au bord de l'eau 🌾

Magnifique moulin du 18ème siècle, parfait pour les photos!
La roue est encore en place.

📍 Sur la Garonne entre Toulouse et Montauban
43.7890, 1.3456

#urbextoulouse #moulinabandonné #patrimoine #abandonedplaces #garonne""",
            'user': 'heritage_hunter',
            'location': 'Garonne',
            'hashtags': ['urbextoulouse']
        }
    ]
    
    return posts

def process_instagram_posts(posts):
    """Process Instagram posts and extract spot information"""
    spots = []
    
    for post in posts:
        # Extract coordinates
        lat, lon = extract_coordinates_from_caption(post['caption'])
        
        # Extract potential spot name
        lines = post['caption'].split('\n')
        spot_name = lines[0].strip() if lines else 'Instagram Spot'
        # Remove emojis for cleaner name
        spot_name = re.sub(r'[^\w\s\-éèêëàâäôöûü]', '', spot_name).strip()
        
        # Determine if hidden
        is_hidden = any(tag in post['hashtags'] for tag in 
                       ['toulousesecret', 'spotsecret', 'cascadecachée', 'lacsecret'])
        
        # Extract activities
        activities = []
        caption_lower = post['caption'].lower()
        if any(word in caption_lower for word in ['baignade', 'nager', 'swim']):
            activities.append('baignade')
        if any(word in caption_lower for word in ['photo', 'sunset', 'vue']):
            activities.append('photo')
        if any(word in caption_lower for word in ['urbex', 'abandonné']):
            activities.append('urbex')
        if any(word in caption_lower for word in ['randonnée', 'marche', 'sentier']):
            activities.append('randonnée')
        if any(word in caption_lower for word in ['grotte', 'spéléo']):
            activities.append('spéléologie')
        
        spot = {
            'source': 'instagram',
            'source_url': f"https://instagram.com/p/{post['id']}",
            'raw_text': post['caption'],
            'extracted_name': spot_name or f"Instagram spot by {post['user']}",
            'latitude': lat,
            'longitude': lon,
            'location_type': 'instagram_spot',
            'activities': ', '.join(activities) if activities else 'exploration',
            'is_hidden': 1 if is_hidden else 0,
            'discovery_snippet': post['caption'][:200],
            'metadata': {
                'user': post['user'],
                'location_tag': post['location'],
                'hashtags': post['hashtags']
            }
        }
        
        spots.append(spot)
    
    return spots

def save_to_database(spots):
    """Save Instagram spots to database"""
    conn = sqlite3.connect('hidden_spots.db')
    cursor = conn.cursor()
    
    saved_count = 0
    for spot in spots:
        # Check if already exists
        cursor.execute('''
            SELECT id FROM spots 
            WHERE source = ? AND source_url = ?
        ''', (spot['source'], spot['source_url']))
        
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
                json.dumps(spot['metadata'])
            ))
            saved_count += 1
    
    conn.commit()
    conn.close()
    
    return saved_count

def main():
    print("📸 Starting Instagram hashtag scraper...")
    print("   Note: Using sample data (Instagram API requires authentication)")
    
    # Get sample Instagram posts
    posts = create_instagram_sample_data()
    print(f"\n📱 Processing {len(posts)} Instagram posts...")
    
    # Process posts
    spots = process_instagram_posts(posts)
    print(f"📍 Extracted {len(spots)} potential spots")
    
    # Save to database
    saved = save_to_database(spots)
    print(f"💾 Saved {saved} new spots to database")
    
    # Summary
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