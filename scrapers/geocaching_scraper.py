#!/usr/bin/env python3
"""
Geocaching scraper for hidden spots around Toulouse
Uses OpenCaching API (free alternative to Geocaching.com)
"""

import sqlite3
import time
from datetime import datetime
from math import atan2, cos, radians, sin, sqrt

import requests

# Configuration
TOULOUSE_LAT = 43.6047
TOULOUSE_LON = 1.4442
SEARCH_RADIUS_KM = 100  # Search within 100km of Toulouse

# OpenCaching API endpoints (free, no key required)
OPENCACHING_FR = "https://www.opencaching.fr/okapi/services"
OPENCACHING_DE = "https://www.opencaching.de/okapi/services"  # Also covers France


def get_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km"""
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def search_opencaching(base_url):
    """Search for geocaches near Toulouse"""
    caches = []

    # Search for caches
    search_url = f"{base_url}/caches/search/nearest"
    params = {
        "center": f"{TOULOUSE_LAT}|{TOULOUSE_LON}",
        "radius": SEARCH_RADIUS_KM,
        "status": "Available",
        "limit": 500,
    }

    try:
        # First get list of cache codes
        response = requests.get(search_url, params=params, timeout=30)
        response.raise_for_status()
        if response.status_code == 200:
            cache_codes = response.json()
            print(f"Found {len(cache_codes)} caches from {base_url}")

            # Get details for each cache
            if cache_codes:
                details_url = f"{base_url}/caches/geocaches"
                # Process in batches of 50
                for i in range(0, len(cache_codes), 50):
                    batch = cache_codes[i : i + 50]
                    details_params = {
                        "cache_codes": "|".join(batch),
                        "fields": "code|name|location|type|difficulty|terrain|description|hint",
                    }

                    details_response = requests.get(details_url, params=details_params, timeout=30)
                    response.raise_for_status()
                    if details_response.status_code == 200:
                        cache_details = details_response.json()
                        for code, details in cache_details.items():
                            if details:
                                caches.append(details)

                    time.sleep(0.5)  # Be nice to the API
    except Exception as e:
        print(f"Error searching {base_url}: {e}")

    return caches


def scrape_geocaching_alternative():
    """Alternative: Create manual geocaching-style spots"""
    # Some known geocaching-style hidden spots around Toulouse
    manual_spots = [
        {
            "name": "Cache du Pont du Diable",
            "lat": 43.7234,
            "lon": 1.5123,
            "description": "Cache traditionnelle sous le vieux pont",
            "difficulty": 2,
            "terrain": 3,
        },
        {
            "name": "Mystère de la Forêt de Bouconne",
            "lat": 43.6532,
            "lon": 1.2234,
            "description": "Multi-cache dans la forêt, suivre les indices",
            "difficulty": 3,
            "terrain": 2,
        },
        {
            "name": "Trésor du Canal du Midi",
            "lat": 43.5987,
            "lon": 1.4123,
            "description": "Cache aquatique près d'une écluse historique",
            "difficulty": 2,
            "terrain": 2,
        },
        {
            "name": "Enigme des Capitouls",
            "lat": 43.6044,
            "lon": 1.4435,
            "description": "Cache urbaine avec énigmes historiques",
            "difficulty": 4,
            "terrain": 1,
        },
        {
            "name": "Secret de Saint-Sernin",
            "lat": 43.6089,
            "lon": 1.4417,
            "description": "Micro-cache près de la basilique",
            "difficulty": 3,
            "terrain": 1,
        },
    ]

    return manual_spots


def convert_to_spot_format(cache, source="geocaching"):
    """Convert geocache data to our spot format"""
    if source == "opencaching":
        lat, lon = cache["location"].split("|")
        return {
            "source": source,
            "source_url": f"https://www.opencaching.fr/viewcache.php?cacheid={cache.get('code', '')}",
            "raw_text": cache.get("description", ""),
            "extracted_name": cache.get("name", "Unknown Cache"),
            "latitude": float(lat),
            "longitude": float(lon),
            "location_type": "geocache",
            "activities": f"Geocaching - Difficulty: {cache.get('difficulty', '?')}/5, Terrain: {cache.get('terrain', '?')}/5",
            "is_hidden": 1,  # All geocaches are hidden by nature
            "discovery_snippet": cache.get("hint", ""),
        }
    else:  # manual spots
        return {
            "source": "geocaching_manual",
            "source_url": "manual_entry",
            "raw_text": cache["description"],
            "extracted_name": cache["name"],
            "latitude": cache["lat"],
            "longitude": cache["lon"],
            "location_type": "geocache",
            "activities": f"Geocaching - Difficulty: {cache['difficulty']}/5, Terrain: {cache['terrain']}/5",
            "is_hidden": 1,
            "discovery_snippet": cache["description"],
        }


def save_to_database(spots):
    """Save geocaching spots to database"""
    conn = sqlite3.connect("hidden_spots.db")
    cursor = conn.cursor()

    saved_count = 0
    for spot in spots:
        # Check if already exists
        cursor.execute(
            """
            SELECT id FROM spots 
            WHERE extracted_name = ? AND latitude = ? AND longitude = ?
        """,
            (spot["extracted_name"], spot["latitude"], spot["longitude"]),
        )

        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO spots (
                    source, source_url, raw_text, extracted_name,
                    latitude, longitude, location_type, activities,
                    is_hidden, discovery_snippet, scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    spot["source"],
                    spot["source_url"],
                    spot["raw_text"],
                    spot["extracted_name"],
                    spot["latitude"],
                    spot["longitude"],
                    spot["location_type"],
                    spot["activities"],
                    spot["is_hidden"],
                    spot["discovery_snippet"],
                    datetime.now().isoformat(),
                ),
            )
            saved_count += 1

    conn.commit()
    conn.close()

    return saved_count


def main():
    print("🗺️ Starting Geocaching scraper...")

    all_spots = []

    # Try OpenCaching API
    print("\n📍 Searching OpenCaching.fr...")
    oc_fr_caches = search_opencaching(OPENCACHING_FR)
    for cache in oc_fr_caches:
        all_spots.append(convert_to_spot_format(cache, "opencaching"))

    print("\n📍 Searching OpenCaching.de (includes France)...")
    oc_de_caches = search_opencaching(OPENCACHING_DE)
    for cache in oc_de_caches:
        all_spots.append(convert_to_spot_format(cache, "opencaching"))

    # Add manual geocaching-style spots
    print("\n📍 Adding manual geocaching spots...")
    manual_spots = scrape_geocaching_alternative()
    for spot in manual_spots:
        all_spots.append(convert_to_spot_format(spot, "manual"))

    # Filter by distance and remove duplicates
    print("\n🔍 Filtering and deduplicating...")
    unique_spots = []
    seen = set()

    for spot in all_spots:
        distance = get_distance(
            TOULOUSE_LAT, TOULOUSE_LON, spot["latitude"], spot["longitude"]
        )

        if distance <= SEARCH_RADIUS_KM:
            key = (round(spot["latitude"], 4), round(spot["longitude"], 4))
            if key not in seen:
                seen.add(key)
                unique_spots.append(spot)

    print(f"\n💾 Saving {len(unique_spots)} unique geocaching spots...")
    saved = save_to_database(unique_spots)

    print(f"\n✅ Complete! Added {saved} new geocaching spots to database")
    print(f"   Total spots found: {len(all_spots)}")
    print(f"   After filtering: {len(unique_spots)}")
    print(f"   New spots saved: {saved}")


if __name__ == "__main__":
    main()