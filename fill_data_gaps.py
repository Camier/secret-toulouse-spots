#!/usr/bin/env python3
"""
Fill gaps in the secret spots data:
1. Geocode spots without coordinates
2. Clean up bad names
3. Remove duplicates
4. Enrich data with additional info
"""

import re
import sqlite3
import time
from datetime import datetime

from geopy.distance import geodesic
from geopy.geocoders import Nominatim

# Toulouse center coordinates
TOULOUSE_CENTER = (43.6047, 1.4442)


def extract_better_name(raw_text):
    """Extract a better name from the raw text"""
    # Remove common prefixes
    text = raw_text.replace("Se baigner autour de Toulouse", "").strip()
    text = text.replace("Spots de baignades à Toulouse ?", "").strip()
    text = text.replace("New Year's Eve in Toulouse", "").strip()

    # Look for location mentions
    location_patterns = [
        r"(?:cascade|lac|plage|grotte|pont|château|moulin|source|fontaine|gorges?|rivière)\s+(?:de |du |des |d\')?([A-Z][a-zéèêëàâäôöûü\-]+(?:\s+[A-Z][a-zéèêëàâäôöûü\-]+)*)",
        r"(?:à |au |aux |près de |proche de )?([A-Z][a-zéèêëàâäôöûü\-]+(?:\s+[A-Z][a-zéèêëàâäôöûü\-]+)*)",
    ]

    for pattern in location_patterns:
        match = re.search(pattern, text)
        if match:
            name = match.group(1)
            # Add context if it's a known type
            if "cascade" in text.lower():
                return f"Cascade de {name}"
            elif "lac" in text.lower():
                return f"Lac de {name}"
            elif "grotte" in text.lower():
                return f"Grotte de {name}"
            elif "gorges" in text.lower():
                return f"Gorges de {name}"
            return name

    # Extract first meaningful sentence
    sentences = text.split(".")
    if sentences:
        first = sentences[0].strip()
        if len(first) > 10 and len(first) < 100:
            return first[:50]

    return None


def geocode_location(location_text, geolocator):
    """Try to geocode a location from text"""
    # Extract location mentions
    locations = []

    # Common location patterns
    location_keywords = [
        "toulouse",
        "muret",
        "blagnac",
        "colomiers",
        "tournefeuille",
        "saint-gaudens",
        "albi",
        "montauban",
        "castres",
        "pamiers",
        "foix",
        "mazamet",
        "saint-antonin-noble-val",
        "aspet",
        "ariège",
        "haute-garonne",
        "tarn",
        "aveyron",
    ]

    text_lower = location_text.lower()
    for keyword in location_keywords:
        if keyword in text_lower:
            locations.append(keyword)

    # Try to geocode each location
    for loc in locations:
        try:
            # Add region context
            search_query = f"{loc}, Occitanie, France"
            result = geolocator.geocode(search_query)
            if result:
                return result.latitude, result.longitude
            time.sleep(1)  # Rate limit
        except:
            continue

    return None, None


def calculate_distance_from_toulouse(lat, lon):
    """Calculate distance from Toulouse center"""
    if lat and lon:
        spot_coords = (lat, lon)
        return round(geodesic(TOULOUSE_CENTER, spot_coords).kilometers, 1)
    return None


def clean_and_enrich_data():
    """Main function to clean and enrich the data"""
    conn = sqlite3.connect("hidden_spots.db")
    cursor = conn.cursor()

    # Initialize geocoder
    geolocator = Nominatim(user_agent="secret-toulouse-spots")

    print("🧹 Starting data cleanup and enrichment...")

    # 1. Fix bad names
    print("\n📝 Fixing bad names...")
    cursor.execute(
        """
        SELECT id, extracted_name, raw_text 
        FROM spots 
        WHERE length(extracted_name) < 10 
        OR extracted_name IN ('Affichage', 'Endroit', 'Grotte')
    """
    )

    bad_names = cursor.fetchall()
    fixed_count = 0

    for spot_id, old_name, raw_text in bad_names:
        better_name = extract_better_name(raw_text)
        if better_name and better_name != old_name:
            cursor.execute(
                """
                UPDATE spots 
                SET extracted_name = ?,
                    metadata = json_set(
                        COALESCE(metadata, '{}'),
                        '$.original_bad_name', ?,
                        '$.name_fixed_at', ?
                    )
                WHERE id = ?
            """,
                (better_name, old_name, datetime.now().isoformat(), spot_id),
            )
            fixed_count += 1
            print(f"  Fixed: '{old_name}' → '{better_name}'")

    print(f"  ✅ Fixed {fixed_count} bad names")

    # 2. Remove exact duplicates
    print("\n🔍 Removing duplicates...")
    cursor.execute(
        """
        WITH duplicates AS (
            SELECT id, extracted_name, latitude, longitude,
                   ROW_NUMBER() OVER (
                       PARTITION BY extracted_name, latitude, longitude 
                       ORDER BY scraped_at DESC
                   ) as rn
            FROM spots
        )
        DELETE FROM spots 
        WHERE id IN (
            SELECT id FROM duplicates WHERE rn > 1
        )
    """
    )

    duplicates_removed = cursor.rowcount
    print(f"  ✅ Removed {duplicates_removed} exact duplicates")

    # 3. Geocode spots without coordinates
    print("\n📍 Geocoding spots without coordinates...")
    cursor.execute(
        """
        SELECT id, extracted_name, raw_text 
        FROM spots 
        WHERE latitude IS NULL OR longitude IS NULL
    """
    )

    no_coords = cursor.fetchall()
    geocoded_count = 0

    for spot_id, name, raw_text in no_coords:
        lat, lon = geocode_location(f"{name} {raw_text}", geolocator)
        if lat and lon:
            cursor.execute(
                """
                UPDATE spots 
                SET latitude = ?, 
                    longitude = ?,
                    location_type = 'geocoded',
                    metadata = json_set(
                        COALESCE(metadata, '{}'),
                        '$.geocoded', true,
                        '$.geocoded_at', ?
                    )
                WHERE id = ?
            """,
                (lat, lon, datetime.now().isoformat(), spot_id),
            )
            geocoded_count += 1
            print(f"  Geocoded: {name} → {lat}, {lon}")

    print(f"  ✅ Geocoded {geocoded_count} spots")

    # 4. Add distance from Toulouse
    print("\n📏 Calculating distances from Toulouse...")
    cursor.execute(
        """
        SELECT id, latitude, longitude 
        FROM spots 
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """
    )

    with_coords = cursor.fetchall()
    for spot_id, lat, lon in with_coords:
        distance = calculate_distance_from_toulouse(lat, lon)
        if distance:
            cursor.execute(
                """
                UPDATE spots 
                SET metadata = json_set(
                    COALESCE(metadata, '{}'),
                    '$.distance_from_toulouse_km', ?
                )
                WHERE id = ?
            """,
                (distance, spot_id),
            )

    print(f"  ✅ Added distances for {len(with_coords)} spots")

    # 5. Improve activity tags
    print("\n🏃 Improving activity tags...")
    cursor.execute("SELECT id, raw_text, activities FROM spots")
    all_spots = cursor.fetchall()

    activity_keywords = {
        "baignade": [
            "baigner",
            "nager",
            "piscine",
            "plage",
            "cascade",
            "lac",
            "rivière",
        ],
        "randonnée": ["randonnée", "rando", "marche", "sentier", "trek", "balade"],
        "escalade": ["escalade", "grimpe", "varappe"],
        "VTT": ["vtt", "vélo", "bike", "cyclisme"],
        "photo": [
            "photo",
            "photographe",
            "vue",
            "panorama",
            "sunset",
            "lever de soleil",
        ],
        "pique-nique": ["pique-nique", "picnic", "bbq", "barbecue"],
        "urbex": ["urbex", "abandonné", "exploration urbaine", "friche"],
        "spéléologie": ["spéléo", "grotte", "caverne", "gouffre"],
        "pêche": ["pêche", "poisson", "truite"],
        "kayak": ["kayak", "canoë", "paddle", "raft"],
        "camping": ["camping", "bivouac", "tente"],
        "observation": ["observer", "oiseaux", "faune", "flore"],
    }

    updated_activities = 0
    for spot_id, raw_text, current_activities in all_spots:
        text_lower = raw_text.lower() if raw_text else ""
        new_activities = []

        for activity, keywords in activity_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                new_activities.append(activity)

        if new_activities and (
            not current_activities or current_activities == "exploration"
        ):
            activities_str = ", ".join(new_activities)
            cursor.execute(
                """
                UPDATE spots 
                SET activities = ?
                WHERE id = ?
            """,
                (activities_str, spot_id),
            )
            updated_activities += 1

    print(f"  ✅ Updated activities for {updated_activities} spots")

    # Commit all changes
    conn.commit()

    # 6. Generate summary report
    print("\n📊 Generating summary report...")

    cursor.execute(
        """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 ELSE 0 END) as with_coords,
            SUM(CASE WHEN is_hidden = 1 THEN 1 ELSE 0 END) as hidden,
            SUM(CASE WHEN json_extract(metadata, '$.geocoded') = 1 THEN 1 ELSE 0 END) as geocoded,
            SUM(CASE WHEN json_extract(metadata, '$.distance_from_toulouse_km') IS NOT NULL THEN 1 ELSE 0 END) as with_distance
        FROM spots
    """
    )

    stats = cursor.fetchone()
    print(f"\n✅ Data cleanup complete!")
    print(f"   Total spots: {stats[0]}")
    print(f"   With coordinates: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)")
    print(f"   Hidden/secret: {stats[2]} ({stats[2]/stats[0]*100:.1f}%)")
    print(f"   Geocoded: {stats[3]}")
    print(f"   With distance: {stats[4]}")

    # Show remaining spots without coordinates
    cursor.execute(
        """
        SELECT id, extracted_name 
        FROM spots 
        WHERE latitude IS NULL OR longitude IS NULL
    """
    )

    no_coords_remaining = cursor.fetchall()
    if no_coords_remaining:
        print(f"\n⚠️  Still missing coordinates for {len(no_coords_remaining)} spots:")
        for spot_id, name in no_coords_remaining[:5]:
            print(f"   - {name} (ID: {spot_id})")
        if len(no_coords_remaining) > 5:
            print(f"   ... and {len(no_coords_remaining) - 5} more")

    conn.close()


if __name__ == "__main__":
    # Install required package if needed
    try:
        from geopy.geocoders import Nominatim
    except ImportError:
        print("Installing geopy for geocoding...")
        import subprocess

        subprocess.check_call([sys.executable, "-m", "pip", "install", "geopy"])
        from geopy.geocoders import Nominatim

    clean_and_enrich_data()
