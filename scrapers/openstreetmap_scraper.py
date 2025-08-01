#!/usr/bin/env python3
"""
OpenStreetMap scraper for finding hidden natural spots around Toulouse
Uses Overpass API to find water features, viewpoints, caves, etc.
"""

import json
import sqlite3
import time
from datetime import datetime

import requests

# Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Bounding box around Toulouse (roughly 100km radius)
# South, West, North, East
BBOX = "42.5,0.5,44.5,2.5"

# OSM queries for different types of hidden spots
OSM_QUERIES = {
    "waterfalls": """
        [out:json][timeout:25];
        (
          node["waterway"="waterfall"]({bbox});
          way["waterway"="waterfall"]({bbox});
        );
        out body;
        >;
        out skel qt;
    """,
    "swimming_spots": """
        [out:json][timeout:25];
        (
          node["natural"="water"]["sport"="swimming"]({bbox});
          way["natural"="water"]["sport"="swimming"]({bbox});
          node["leisure"="swimming_area"]({bbox});
          way["leisure"="swimming_area"]({bbox});
        );
        out body;
        >;
        out skel qt;
    """,
    "viewpoints": """
        [out:json][timeout:25];
        (
          node["tourism"="viewpoint"]({bbox});
        );
        out body;
        >;
        out skel qt;
    """,
    "caves": """
        [out:json][timeout:25];
        (
          node["natural"="cave_entrance"]({bbox});
          way["natural"="cave_entrance"]({bbox});
        );
        out body;
        >;
        out skel qt;
    """,
    "ruins": """
        [out:json][timeout:25];
        (
          node["historic"="ruins"]({bbox});
          way["historic"="ruins"]({bbox});
          node["ruins"="yes"]({bbox});
          way["ruins"="yes"]({bbox});
        );
        out body;
        >;
        out skel qt;
    """,
    "springs": """
        [out:json][timeout:25];
        (
          node["natural"="spring"]({bbox});
          node["natural"="hot_spring"]({bbox});
        );
        out body;
        >;
        out skel qt;
    """,
}


def query_overpass(query_template, bbox):
    """Execute an Overpass API query"""
    query = query_template.replace("{bbox}", bbox)

    try:
        response = requests.post(OVERPASS_URL, data={"data": query}, timeout=30)
        response.raise_for_status()
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: Status code {response.status_code}")
            return None
    except Exception as e:
        print(f"Error querying Overpass: {e}")
        return None


def process_osm_data(data, spot_type):
    """Process OSM data into our spot format"""
    spots = []

    if not data or "elements" not in data:
        return spots

    for element in data["elements"]:
        # Skip if no coordinates
        if "lat" not in element or "lon" not in element:
            continue

        # Extract name
        tags = element.get("tags", {})
        name = tags.get("name", tags.get("name:fr", ""))

        # Skip unnamed features unless they're interesting
        if not name and spot_type not in ["waterfalls", "caves", "springs"]:
            continue

        # Generate name if missing
        if not name:
            if spot_type == "waterfalls":
                name = (
                    f"Cascade non nommée ({element['lat']:.4f}, {element['lon']:.4f})"
                )
            elif spot_type == "caves":
                name = f"Grotte non nommée ({element['lat']:.4f}, {element['lon']:.4f})"
            elif spot_type == "springs":
                name = f"Source non nommée ({element['lat']:.4f}, {element['lon']:.4f})"
            else:
                name = f"{spot_type} ({element['lat']:.4f}, {element['lon']:.4f})"

        # Build description from tags
        description_parts = []
        if tags.get("description"):
            description_parts.append(tags["description"])
        if tags.get("description:fr"):
            description_parts.append(tags["description:fr"])
        if tags.get("access"):
            description_parts.append(f"Accès: {tags['access']}")
        if tags.get("ele"):
            description_parts.append(f"Altitude: {tags['ele']}m")

        description = " ".join(description_parts) or f"Point OSM de type {spot_type}"

        # Determine if it's hidden (based on access and other factors)
        is_hidden = 0
        if tags.get("access") in ["private", "permissive", "no"]:
            is_hidden = 1
        if "abandoned" in tags.get("description", "").lower():
            is_hidden = 1
        if tags.get("ruins") == "yes":
            is_hidden = 1

        # Map OSM types to our location types
        location_type_map = {
            "waterfalls": "water",
            "swimming_spots": "water",
            "viewpoints": "viewpoint",
            "caves": "nature",
            "ruins": "historic",
            "springs": "water",
        }

        # Determine activities
        activities = []
        if spot_type in ["waterfalls", "swimming_spots", "springs"]:
            activities.append("baignade")
        if spot_type == "viewpoints":
            activities.append("photo")
        if spot_type == "caves":
            activities.append("spéléologie")
        if spot_type == "ruins":
            activities.append("exploration")
            activities.append("photo")
        activities.append("randonnée")  # Most spots require some walking

        spot = {
            "source": f"osm_{spot_type}",
            "source_url": f"https://www.openstreetmap.org/{element['type']}/{element['id']}",
            "raw_text": description,
            "extracted_name": name,
            "latitude": element["lat"],
            "longitude": element["lon"],
            "location_type": location_type_map.get(spot_type, "other"),
            "activities": ", ".join(set(activities)),
            "is_hidden": is_hidden,
            "discovery_snippet": description[:200],
            "metadata": {
                "osm_id": element["id"],
                "osm_type": element["type"],
                "osm_tags": tags,
            },
        }

        spots.append(spot)

    return spots


def save_to_database(spots):
    """Save OSM spots to database"""
    conn = sqlite3.connect("hidden_spots.db")
    cursor = conn.cursor()

    saved_count = 0
    for spot in spots:
        # Check if already exists (by OSM ID)
        osm_id = spot["metadata"]["osm_id"]
        cursor.execute(
            """
            SELECT id FROM spots 
            WHERE json_extract(metadata, '$.osm_id') = ?
        """,
            (osm_id,),
        )

        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO spots (
                    source, source_url, raw_text, extracted_name,
                    latitude, longitude, location_type, activities,
                    is_hidden, discovery_snippet, scraped_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    json.dumps(spot["metadata"]),
                ),
            )
            saved_count += 1

    conn.commit()
    conn.close()

    return saved_count


def main():
    print("🗺️ Starting OpenStreetMap scraper...")
    print(f"   Searching area: {BBOX}")

    all_spots = []

    # Query each type of spot
    for spot_type, query in OSM_QUERIES.items():
        print(f"\n🔍 Searching for {spot_type}...")

        data = query_overpass(query, BBOX)
        if data:
            spots = process_osm_data(data, spot_type)
            print(f"   Found {len(spots)} {spot_type}")
            all_spots.extend(spots)

        # Be nice to the API
        time.sleep(2)

    # Remove duplicates based on coordinates
    print(f"\n🔍 Removing duplicates...")
    unique_spots = []
    seen_coords = set()

    for spot in all_spots:
        coord_key = (round(spot["latitude"], 5), round(spot["longitude"], 5))
        if coord_key not in seen_coords:
            seen_coords.add(coord_key)
            unique_spots.append(spot)

    print(
        f"   Unique spots: {len(unique_spots)} (removed {len(all_spots) - len(unique_spots)} duplicates)"
    )

    # Save to database
    print(f"\n💾 Saving to database...")
    saved = save_to_database(unique_spots)

    # Summary
    print(f"\n✅ Complete!")
    print(f"   Total spots found: {len(all_spots)}")
    print(f"   Unique spots: {len(unique_spots)}")
    print(f"   New spots saved: {saved}")

    # Breakdown by type
    type_counts = {}
    for spot in unique_spots:
        source = spot["source"]
        type_counts[source] = type_counts.get(source, 0) + 1

    print(f"\n📊 By type:")
    for source, count in sorted(type_counts.items()):
        print(f"   {source}: {count}")


if __name__ == "__main__":
    main()