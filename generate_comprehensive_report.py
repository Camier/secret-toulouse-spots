#!/usr/bin/env python3
"""Generate comprehensive report of all scraped hidden spots"""

import sqlite3
from datetime import datetime
import json
from collections import defaultdict

def generate_comprehensive_report():
    """Generate a complete report of all discovered hidden spots"""
    
    conn = sqlite3.connect("hidden_spots.db")
    cursor = conn.cursor()
    
    # Get total counts
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_hidden = 1 THEN 1 ELSE 0 END) as hidden,
            COUNT(DISTINCT source) as sources
        FROM scraped_locations
    """)
    total, hidden, sources = cursor.fetchone()
    
    print("🗺️ COMPREHENSIVE HIDDEN SPOTS REPORT")
    print("=" * 60)
    print(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"📍 Total Locations: {total}")
    print(f"🔐 Hidden/Secret Spots: {hidden}")
    print(f"📡 Data Sources: {sources}")
    print("=" * 60)
    
    # Get locations by type
    print("\n📊 LOCATIONS BY TYPE:")
    cursor.execute("""
        SELECT location_type, COUNT(*) as count, 
               SUM(CASE WHEN is_hidden = 1 THEN 1 ELSE 0 END) as hidden_count
        FROM scraped_locations
        GROUP BY location_type
        ORDER BY count DESC
    """)
    
    for loc_type, count, hidden_count in cursor.fetchall():
        print(f"  • {loc_type or 'unspecified'}: {count} total ({hidden_count} hidden)")
    
    # Get locations by activity
    print("\n🏃 LOCATIONS BY ACTIVITY:")
    cursor.execute("""
        SELECT activities, COUNT(*) as count
        FROM scraped_locations
        WHERE activities IS NOT NULL
        GROUP BY activities
        ORDER BY count DESC
        LIMIT 10
    """)
    
    for activities, count in cursor.fetchall():
        print(f"  • {activities}: {count} spots")
    
    # Get top hidden spots with coordinates
    print("\n🎯 TOP SECRET SPOTS WITH GPS COORDINATES:")
    cursor.execute("""
        SELECT extracted_name, latitude, longitude, location_type, activities, source
        FROM scraped_locations
        WHERE is_hidden = 1 
        AND latitude IS NOT NULL 
        AND longitude IS NOT NULL
        ORDER BY scraped_at DESC
        LIMIT 15
    """)
    
    for name, lat, lng, loc_type, activities, source in cursor.fetchall():
        print(f"\n  📍 {name}")
        print(f"     GPS: {lat:.4f}, {lng:.4f}")
        print(f"     Type: {loc_type} | Activities: {activities}")
        print(f"     Source: {source}")
    
    # Get spots by source
    print("\n\n📡 BREAKDOWN BY SOURCE:")
    cursor.execute("""
        SELECT source, 
               COUNT(*) as total,
               SUM(CASE WHEN is_hidden = 1 THEN 1 ELSE 0 END) as hidden,
               COUNT(DISTINCT extracted_name) as unique_names
        FROM scraped_locations
        GROUP BY source
        ORDER BY total DESC
    """)
    
    for source, total, hidden, unique in cursor.fetchall():
        print(f"\n  🔹 {source.upper()}")
        print(f"     Total: {total} | Hidden: {hidden} | Unique: {unique}")
    
    # Special Reddit finds
    print("\n\n🔴 REDDIT EXCLUSIVE FINDS:")
    cursor.execute("""
        SELECT extracted_name, location_type, activities, metadata
        FROM scraped_locations
        WHERE source = 'reddit' 
        AND is_hidden = 1
        ORDER BY scraped_at DESC
    """)
    
    for name, loc_type, activities, metadata in cursor.fetchall():
        print(f"\n  • {name}")
        print(f"    Type: {loc_type} | Activities: {activities}")
        if metadata:
            try:
                meta = json.loads(metadata)
                if 'coordinates_provided' in meta:
                    print(f"    ⭐ User provided exact coordinates!")
                if 'security' in meta:
                    print(f"    ⚠️ Security: {meta['security']}")
            except:
                pass
    
    # Water spots summary
    print("\n\n💧 WATER SPOTS SUMMARY:")
    cursor.execute("""
        SELECT extracted_name, location_type, activities, latitude, longitude
        FROM scraped_locations
        WHERE (location_type IN ('lake', 'river', 'waterfall', 'natural_pool') 
               OR activities LIKE '%swimming%'
               OR activities LIKE '%baignade%')
        AND latitude IS NOT NULL
        ORDER BY is_hidden DESC, extracted_name
        LIMIT 20
    """)
    
    water_spots = cursor.fetchall()
    for name, loc_type, activities, lat, lng in water_spots:
        print(f"  • {name} ({loc_type})")
        print(f"    GPS: {lat:.4f}, {lng:.4f} | Activities: {activities}")
    
    # Hot springs
    print("\n\n♨️ HOT SPRINGS (SOURCES CHAUDES):")
    cursor.execute("""
        SELECT extracted_name, latitude, longitude, metadata
        FROM scraped_locations
        WHERE location_type = 'hot_spring' 
        OR activities LIKE '%thermal%'
        OR extracted_name LIKE '%source%chaude%'
    """)
    
    for name, lat, lng, metadata in cursor.fetchall():
        print(f"  • {name}")
        if lat and lng:
            print(f"    GPS: {lat:.4f}, {lng:.4f}")
    
    # Urbex spots
    print("\n\n🏚️ URBEX LOCATIONS:")
    cursor.execute("""
        SELECT extracted_name, location_type, metadata
        FROM scraped_locations
        WHERE location_type = 'urbex' 
        OR activities LIKE '%urbex%'
        OR activities LIKE '%exploration%'
        OR location_type LIKE '%abandon%'
    """)
    
    for name, loc_type, metadata in cursor.fetchall():
        print(f"  • {name}")
        if metadata:
            try:
                meta = json.loads(metadata)
                if 'security' in meta:
                    print(f"    ⚠️ {meta['security']}")
            except:
                pass
    
    # Caves and grottos
    print("\n\n🕳️ CAVES & GROTTOS:")
    cursor.execute("""
        SELECT extracted_name, latitude, longitude, activities
        FROM scraped_locations
        WHERE location_type IN ('cave', 'grotto', 'gouffre')
        OR extracted_name LIKE '%grotte%'
        OR extracted_name LIKE '%gouffre%'
        ORDER BY extracted_name
    """)
    
    for name, lat, lng, activities in cursor.fetchall():
        print(f"  • {name}")
        if lat and lng:
            print(f"    GPS: {lat:.4f}, {lng:.4f}")
        if activities:
            print(f"    Activities: {activities}")
    
    # Generate distance analysis from Toulouse
    print("\n\n📏 DISTANCE ANALYSIS FROM TOULOUSE:")
    cursor.execute("""
        SELECT extracted_name, latitude, longitude,
               (ABS(latitude - 43.6047) + ABS(longitude - 1.4442)) * 111 as approx_km
        FROM scraped_locations
        WHERE latitude IS NOT NULL 
        AND longitude IS NOT NULL
        ORDER BY approx_km
        LIMIT 10
    """)
    
    print("  Closest spots to Toulouse:")
    for name, lat, lng, dist in cursor.fetchall():
        print(f"  • {name}: ~{dist:.1f} km")
    
    # Export data
    print("\n\n💾 EXPORTING DATA...")
    
    # Export to JSON
    cursor.execute("""
        SELECT * FROM scraped_locations
        WHERE is_hidden = 1
        ORDER BY scraped_at DESC
    """)
    
    columns = [description[0] for description in cursor.description]
    hidden_spots = []
    
    for row in cursor.fetchall():
        spot = dict(zip(columns, row))
        hidden_spots.append(spot)
    
    with open('hidden_spots_export.json', 'w', encoding='utf-8') as f:
        json.dump(hidden_spots, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"  ✓ Exported {len(hidden_spots)} hidden spots to hidden_spots_export.json")
    
    # Export GPS coordinates for mapping
    cursor.execute("""
        SELECT extracted_name, latitude, longitude, location_type, activities
        FROM scraped_locations
        WHERE latitude IS NOT NULL 
        AND longitude IS NOT NULL
    """)
    
    with open('spots_coordinates.csv', 'w', encoding='utf-8') as f:
        f.write("name,latitude,longitude,type,activities\n")
        for row in cursor.fetchall():
            name = row[0].replace('"', '""')
            f.write(f'"{name}",{row[1]},{row[2]},{row[3]},{row[4]}\n')
    
    print("  ✓ Exported GPS coordinates to spots_coordinates.csv")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ REPORT GENERATION COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    generate_comprehensive_report()