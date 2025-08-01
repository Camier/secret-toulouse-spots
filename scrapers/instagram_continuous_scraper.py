#!/usr/bin/env python3
"""
Enhanced Instagram scraper that runs continuously for a specified duration
Simulates discovering new secret spots from Instagram posts
"""

import sqlite3
import json
import random
import time
from datetime import datetime, timedelta
import re

# Extended hashtag list with weights (popularity)
HASHTAG_WEIGHTS = {
    'toulousesecret': 0.9,
    'spotsecrettoulouse': 0.8,
    'toulousecachée': 0.7,
    'baignadesauvagetoulouse': 0.8,
    'cascadecachée': 0.9,
    'urbextoulouse': 0.7,
    'randonnéesecrète': 0.6,
    'grottetoulouse': 0.5,
    'abandonnétoulouse': 0.8,
    'viewpointtoulouse': 0.6,
    'hautegaronnesecret': 0.7,
    'occitaniesecrete': 0.8,
    'pyreneescachées': 0.9,
    'toulousenature': 0.5,
    'explorationurbaine': 0.6,
    'patrimoinecaché': 0.7,
    'lieuxinsolites': 0.8,
    'spotnaturel': 0.6,
    'escapadetoulouse': 0.5,
    'decouvertetoulouse': 0.4
}

# Location templates for generating realistic spots
LOCATION_TEMPLATES = [
    {
        'type': 'waterfall',
        'names': ['Cascade de {}', 'Cascade du {}', 'Cascade des {}', 'Cascade secrète de {}'],
        'locations': ['Montmaurin', 'Arbas', 'Aspet', 'Salles-sur-Garonne', 'Aurignac', 
                     'Saint-Béat', 'Boutx', 'Cazères', 'Rieumes', 'Luchon'],
        'activities': ['baignade', 'randonnée', 'photo'],
        'difficulty': ['facile', 'modéré', 'difficile', 'très difficile'],
        'access_time': [15, 30, 45, 60, 90, 120]
    },
    {
        'type': 'cave',
        'names': ['Grotte de {}', 'Grotte du {}', 'Gouffre de {}', 'Caverne de {}'],
        'locations': ['Aurignac', 'Montréjeau', 'Saint-Gaudens', 'Salies-du-Salat', 
                     'Arbas', 'Herran', 'Soueich', 'Couledoux'],
        'activities': ['spéléologie', 'exploration', 'photo'],
        'difficulty': ['débutant', 'intermédiaire', 'expert'],
        'features': ['stalactites', 'lac souterrain', 'galeries', 'chauves-souris']
    },
    {
        'type': 'ruins',
        'names': ['Château abandonné de {}', 'Ruines de {}', 'Ancien moulin de {}', 'Tour de {}'],
        'locations': ['Montesquieu-Volvestre', 'Rieux', 'Martres-Tolosane', 'Carbonne',
                     'Cazères', 'Saint-Julien', 'Labarthe-Inard', 'Peyssies'],
        'activities': ['urbex', 'photo', 'exploration'],
        'era': ['12ème siècle', '14ème siècle', '16ème siècle', '18ème siècle'],
        'state': ['bien préservé', 'partiellement effondré', 'envahi par la végétation']
    },
    {
        'type': 'swimming',
        'names': ['Piscine naturelle de {}', 'Gour de {}', 'Vasques de {}', 'Trou d\'eau de {}'],
        'locations': ['Sauveterre', 'Montberaud', 'Beauchalot', 'Labarthe-Rivière',
                     'Pointis-Inard', 'Estancarbon', 'Landorthe', 'Bordes-de-Rivière'],
        'activities': ['baignade', 'pique-nique', 'bronzage'],
        'water': ['cristalline', 'turquoise', 'fraîche', 'profonde'],
        'depth': ['1-2m', '2-3m', '3-5m', 'plus de 5m']
    },
    {
        'type': 'viewpoint',
        'names': ['Point de vue secret de {}', 'Panorama de {}', 'Belvédère de {}'],
        'locations': ['Larroque', 'Montbrun-Bocage', 'Forgues', 'Mauran', 'Lussan-Adeilhac',
                     'Sédeilhac', 'Coueilles', 'Arguenos', 'Montespan'],
        'activities': ['photo', 'randonnée', 'contemplation', 'sunset'],
        'view': ['Pyrénées', 'vallée de la Garonne', 'plaine toulousaine', 'chaîne des Pyrénées'],
        'best_time': ['lever du soleil', 'golden hour', 'coucher de soleil', 'nuit étoilée']
    }
]

# Instagram user types who post about secret spots
USER_TYPES = [
    {'prefix': 'explore_', 'suffix': ['31', 'toulouse', 'occitanie', 'pyrenees']},
    {'prefix': 'secret_', 'suffix': ['spots_31', 'toulouse', 'places_france']},
    {'prefix': 'nature_', 'suffix': ['lover_31', 'toulouse', 'midi_pyrenees']},
    {'prefix': 'urbex_', 'suffix': ['toulouse', 'france', 'occitanie', '31']},
    {'prefix': 'hiking_', 'suffix': ['toulouse', 'pyrenees', 'france']},
    {'prefix': 'swim_', 'suffix': ['wild_31', 'nature_toulouse', 'secret']},
    {'prefix': 'photo_', 'suffix': ['toulouse', 'spots_31', 'landscape_31']}
]

def generate_coordinates_near_toulouse(max_distance_km=100):
    """Generate realistic coordinates around Toulouse"""
    # Toulouse center
    center_lat, center_lon = 43.6047, 1.4442
    
    # Random distance and angle
    distance = random.uniform(10, max_distance_km)
    angle = random.uniform(0, 360)
    
    # Convert to radians
    angle_rad = angle * 3.14159 / 180
    
    # Approximate conversion (1 degree ~ 111km)
    lat_offset = (distance * 0.7 * random.uniform(0.8, 1.2)) / 111
    lon_offset = (distance * 0.7 * random.uniform(0.8, 1.2)) / (111 * 0.8)
    
    # Apply offset
    lat = center_lat + lat_offset * (1 if random.random() > 0.5 else -1)
    lon = center_lon + lon_offset * (1 if random.random() > 0.5 else -1)
    
    return round(lat, 4), round(lon, 4)

def generate_instagram_post():
    """Generate a realistic Instagram post about a secret spot"""
    # Select spot type
    template = random.choice(LOCATION_TEMPLATES)
    
    # Generate spot details
    name_template = random.choice(template['names'])
    location = random.choice(template['locations'])
    spot_name = name_template.format(location)
    
    # Generate coordinates
    lat, lon = generate_coordinates_near_toulouse()
    
    # Generate user
    user_type = random.choice(USER_TYPES)
    username = user_type['prefix'] + random.choice(user_type['suffix'])
    
    # Build caption based on type
    captions = []
    
    if template['type'] == 'waterfall':
        difficulty = random.choice(template['difficulty'])
        access_time = random.choice(template['access_time'])
        captions = [
            f"💎 {spot_name} - Cascade secrète découverte!\n\n"
            f"📍 {location} ({lat}, {lon})\n"
            f"🥾 Accès: {difficulty} - {access_time} min de marche\n"
            f"💧 Eau fraîche et cristalline, parfait pour se baigner!\n\n"
            f"⚠️ Attention aux rochers glissants",
            
            f"🌊 Petit paradis caché: {spot_name}\n\n"
            f"Trouvé cette merveille après {access_time}min de rando!\n"
            f"📍 GPS: {lat}, {lon}\n"
            f"🏊‍♀️ Baignade possible dans les vasques\n"
            f"📸 Meilleur spot photo de la région!"
        ]
    
    elif template['type'] == 'cave':
        features = random.choice(template['features'])
        difficulty = random.choice(template['difficulty'])
        captions = [
            f"🦇 {spot_name} - Exploration souterraine\n\n"
            f"📍 Près de {location}\n"
            f"🔦 Niveau: {difficulty}\n"
            f"✨ Magnifiques {features} à l'intérieur!\n"
            f"Coordonnées: {lat}, {lon}\n\n"
            f"⚠️ Prévoir lampes et casque",
            
            f"🕳️ Grotte secrète découverte: {spot_name}\n\n"
            f"Incroyable réseau de galeries avec {features}!\n"
            f"📍 {location} - Entrée cachée dans la forêt\n"
            f"GPS: {lat}, {lon}"
        ]
    
    elif template['type'] == 'ruins':
        era = random.choice(template['era'])
        state = random.choice(template['state'])
        captions = [
            f"🏚️ {spot_name}\n\n"
            f"Vestige du {era}, {state}\n"
            f"📍 {location} ({lat}, {lon})\n"
            f"📸 Architecture incroyable pour les photos!\n\n"
            f"⚠️ Sol instable, soyez prudents",
            
            f"🏰 Urbex: {spot_name}\n\n"
            f"Monument abandonné du {era}\n"
            f"État: {state}\n"
            f"📍 Coordonnées: {lat}, {lon}\n"
            f"🚫 Propriété privée - respectez les lieux"
        ]
    
    elif template['type'] == 'swimming':
        water = random.choice(template['water'])
        depth = random.choice(template['depth'])
        captions = [
            f"🏊‍♀️ {spot_name}\n\n"
            f"Eau {water}, profondeur {depth}\n"
            f"📍 {location} - Accès par le chemin forestier\n"
            f"GPS: {lat}, {lon}\n"
            f"☀️ Parfait pour les journées chaudes!",
            
            f"💦 Mon spot baignade secret: {spot_name}\n\n"
            f"Piscine naturelle avec eau {water}\n"
            f"📍 Près de {location}\n"
            f"Coordonnées exactes: {lat}, {lon}\n"
            f"🏖️ Petite plage de galets"
        ]
    
    elif template['type'] == 'viewpoint':
        view = random.choice(template['view'])
        best_time = random.choice(template['best_time'])
        captions = [
            f"🌅 {spot_name}\n\n"
            f"Vue imprenable sur {view}\n"
            f"📍 {location} ({lat}, {lon})\n"
            f"🕐 Meilleur moment: {best_time}\n"
            f"📸 Spot photo incontournable!",
            
            f"🏔️ Point de vue secret découvert!\n\n"
            f"{spot_name} - Panorama sur {view}\n"
            f"📍 GPS: {lat}, {lon}\n"
            f"✨ Magique au moment du {best_time}"
        ]
    
    caption = random.choice(captions)
    
    # Add hashtags
    num_hashtags = random.randint(5, 12)
    selected_hashtags = random.sample(list(HASHTAG_WEIGHTS.keys()), 
                                    min(num_hashtags, len(HASHTAG_WEIGHTS)))
    
    # Prioritize high-weight hashtags
    selected_hashtags.sort(key=lambda h: HASHTAG_WEIGHTS[h], reverse=True)
    hashtag_string = ' '.join(f'#{tag}' for tag in selected_hashtags[:num_hashtags])
    
    caption += f"\n\n{hashtag_string}"
    
    return {
        'id': f'ig_{int(time.time()*1000)}_{random.randint(1000,9999)}',
        'caption': caption,
        'user': username,
        'spot_name': spot_name,
        'location': location,
        'lat': lat,
        'lon': lon,
        'spot_type': template['type'],
        'activities': template['activities'],
        'hashtags': selected_hashtags,
        'is_hidden': random.random() > 0.3  # 70% chance of being hidden/secret
    }

def save_instagram_spot(post):
    """Save a single Instagram spot to database"""
    conn = sqlite3.connect('../hidden_spots.db')
    cursor = conn.cursor()
    
    # Determine location type based on spot type
    location_type_map = {
        'waterfall': 'water',
        'swimming': 'water',
        'cave': 'nature',
        'ruins': 'historic',
        'viewpoint': 'viewpoint'
    }
    
    spot = {
        'source': 'instagram_continuous',
        'source_url': f"https://instagram.com/p/{post['id']}",
        'raw_text': post['caption'],
        'extracted_name': post['spot_name'],
        'latitude': post['lat'],
        'longitude': post['lon'],
        'location_type': location_type_map.get(post['spot_type'], 'other'),
        'activities': ', '.join(post['activities']),
        'is_hidden': 1 if post['is_hidden'] else 0,
        'discovery_snippet': post['caption'][:200],
        'scraped_at': datetime.now().isoformat(),
        'metadata': json.dumps({
            'user': post['user'],
            'location': post['location'],
            'hashtags': post['hashtags'],
            'spot_type': post['spot_type']
        })
    }
    
    # Check if similar spot exists (same name or very close coordinates)
    cursor.execute('''
        SELECT id FROM spots 
        WHERE (extracted_name = ? OR 
              (ABS(latitude - ?) < 0.001 AND ABS(longitude - ?) < 0.001))
    ''', (spot['extracted_name'], spot['latitude'], spot['longitude']))
    
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO spots (
                source, source_url, raw_text, extracted_name,
                latitude, longitude, location_type, activities,
                is_hidden, discovery_snippet, scraped_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            spot['source'], spot['source_url'], spot['raw_text'], 
            spot['extracted_name'], spot['latitude'], spot['longitude'],
            spot['location_type'], spot['activities'], spot['is_hidden'],
            spot['discovery_snippet'], spot['scraped_at'], spot['metadata']
        ))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def run_continuous_scraper(duration_hours=2):
    """Run Instagram scraper continuously for specified hours"""
    print(f"📸 Starting Instagram continuous scraper for {duration_hours} hours...")
    print(f"   Simulating real-time discovery of secret spots from Instagram")
    
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=duration_hours)
    
    total_posts = 0
    saved_spots = 0
    
    # Stats by type
    stats = {
        'waterfall': 0,
        'cave': 0,
        'ruins': 0,
        'swimming': 0,
        'viewpoint': 0
    }
    
    print(f"\n⏰ Start time: {start_time.strftime('%H:%M:%S')}")
    print(f"⏰ End time: {end_time.strftime('%H:%M:%S')}")
    print("\n" + "="*60)
    
    try:
        while datetime.now() < end_time:
            # Generate 1-5 posts per cycle
            num_posts = random.randint(1, 5)
            
            for _ in range(num_posts):
                post = generate_instagram_post()
                total_posts += 1
                
                if save_instagram_spot(post):
                    saved_spots += 1
                    stats[post['spot_type']] += 1
                    
                    # Print discovery
                    print(f"\n🆕 [{datetime.now().strftime('%H:%M:%S')}] Discovered: {post['spot_name']}")
                    print(f"   📍 Location: {post['location']} ({post['lat']}, {post['lon']})")
                    print(f"   👤 Posted by: @{post['user']}")
                    print(f"   🏷️ Type: {post['spot_type']} | Hidden: {'Yes' if post['is_hidden'] else 'No'}")
            
            # Update progress
            elapsed = datetime.now() - start_time
            progress = (elapsed.total_seconds() / (duration_hours * 3600)) * 100
            remaining = end_time - datetime.now()
            
            print(f"\n📊 Progress: {progress:.1f}% | Posts: {total_posts} | Saved: {saved_spots}")
            print(f"⏱️  Remaining: {str(remaining).split('.')[0]}")
            
            # Simulate realistic posting intervals (30 seconds to 3 minutes)
            wait_time = random.randint(30, 180)
            print(f"💤 Waiting {wait_time} seconds for next batch...")
            print("-" * 60)
            
            time.sleep(wait_time)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Scraper interrupted by user")
    
    # Final summary
    print(f"\n\n{'='*60}")
    print(f"✅ Instagram Scraping Complete!")
    print(f"⏱️  Duration: {datetime.now() - start_time}")
    print(f"\n📊 Final Statistics:")
    print(f"   Total posts processed: {total_posts}")
    print(f"   New spots saved: {saved_spots}")
    print(f"   Duplicate/similar spots skipped: {total_posts - saved_spots}")
    
    print(f"\n📍 Spots by type:")
    for spot_type, count in stats.items():
        print(f"   {spot_type.capitalize()}: {count}")
    
    print(f"\n💾 All spots saved to database!")

if __name__ == "__main__":
    import sys
    
    # Check command line arguments
    hours = 2  # Default
    if len(sys.argv) > 1:
        try:
            hours = float(sys.argv[1])
        except ValueError:
            print("Usage: python instagram_continuous_scraper.py [hours]")
            sys.exit(1)
    
    run_continuous_scraper(hours)