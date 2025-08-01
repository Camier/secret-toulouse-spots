#!/usr/bin/env python3
"""
Spot Verification Workflow
Verifies coordinates, checks for duplicates, and validates spot data
"""

import sqlite3
import requests
from math import radians, cos, sin, asin, sqrt
import json
from datetime import datetime

def haversine(lon1, lat1, lon2, lat2):
    """Calculate distance between two points on Earth (in km)"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 # Radius of earth in kilometers
    return c * r

def verify_coordinates(lat, lon):
    """Verify coordinates are within reasonable range of Toulouse"""
    TOULOUSE_LAT = 43.6047
    TOULOUSE_LON = 1.4442
    MAX_DISTANCE_KM = 200
    
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return False, "Invalid coordinate range"
    
    distance = haversine(TOULOUSE_LON, TOULOUSE_LAT, lon, lat)
    if distance > MAX_DISTANCE_KM:
        return False, f"Too far from Toulouse ({distance:.0f}km)"
    
    return True, f"Valid ({distance:.0f}km from Toulouse)"

def find_duplicates(conn):
    """Find potential duplicate spots based on proximity"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, extracted_name, latitude, longitude 
        FROM spots 
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """)
    
    spots = cursor.fetchall()
    duplicates = []
    
    for i, spot1 in enumerate(spots):
        for spot2 in spots[i+1:]:
            if spot1[2] and spot1[3] and spot2[2] and spot2[3]:
                distance = haversine(spot1[3], spot1[2], spot2[3], spot2[2])
                if distance < 0.1:  # Less than 100 meters
                    duplicates.append({
                        'spot1': {'id': spot1[0], 'name': spot1[1]},
                        'spot2': {'id': spot2[0], 'name': spot2[1]},
                        'distance_m': int(distance * 1000)
                    })
    
    return duplicates

def verify_spot_data(conn):
    """Verify spot data completeness and quality"""
    cursor = conn.cursor()
    
    # Check for missing coordinates
    cursor.execute("SELECT COUNT(*) FROM spots WHERE latitude IS NULL OR longitude IS NULL")
    missing_coords = cursor.fetchone()[0]
    
    # Check for missing names
    cursor.execute("SELECT COUNT(*) FROM spots WHERE extracted_name IS NULL OR extracted_name = ''")
    missing_names = cursor.fetchone()[0]
    
    # Check for suspicious coordinates (0,0)
    cursor.execute("SELECT COUNT(*) FROM spots WHERE latitude = 0 AND longitude = 0")
    zero_coords = cursor.fetchone()[0]
    
    # Get spots outside valid range
    cursor.execute("SELECT id, extracted_name, latitude, longitude FROM spots WHERE latitude IS NOT NULL")
    out_of_range = []
    
    for spot in cursor.fetchall():
        valid, msg = verify_coordinates(spot[2], spot[3])
        if not valid:
            out_of_range.append({
                'id': spot[0],
                'name': spot[1],
                'reason': msg
            })
    
    return {
        'missing_coordinates': missing_coords,
        'missing_names': missing_names,
        'zero_coordinates': zero_coords,
        'out_of_range': out_of_range
    }

def main():
    print("🔍 Starting spot verification workflow...")
    
    conn = sqlite3.connect('hidden_spots.db')
    
    # Step 1: Find duplicates
    print("\n📍 Checking for duplicate spots...")
    duplicates = find_duplicates(conn)
    if duplicates:
        print(f"⚠️  Found {len(duplicates)} potential duplicates:")
        for dup in duplicates[:5]:  # Show first 5
            print(f"   - {dup['spot1']['name']} ↔️ {dup['spot2']['name']} ({dup['distance_m']}m apart)")
    else:
        print("✅ No duplicates found")
    
    # Step 2: Verify data quality
    print("\n📊 Verifying data quality...")
    issues = verify_spot_data(conn)
    
    print(f"   Missing coordinates: {issues['missing_coordinates']} spots")
    print(f"   Missing names: {issues['missing_names']} spots")
    print(f"   Zero coordinates: {issues['zero_coordinates']} spots")
    print(f"   Out of range: {len(issues['out_of_range'])} spots")
    
    if issues['out_of_range']:
        print("\n⚠️  Spots outside valid range:")
        for spot in issues['out_of_range'][:5]:
            print(f"   - {spot['name']}: {spot['reason']}")
    
    # Step 3: Generate verification report
    report = {
        'timestamp': datetime.now().isoformat(),
        'duplicates_found': len(duplicates),
        'data_quality': issues,
        'recommendations': []
    }
    
    if duplicates:
        report['recommendations'].append("Review and merge duplicate spots")
    if issues['missing_coordinates'] > 10:
        report['recommendations'].append("Geocode spots missing coordinates")
    if issues['out_of_range']:
        report['recommendations'].append("Review spots outside 200km range")
    
    # Save report
    with open('workflows/verification_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("\n✅ Verification complete! Report saved to verification_report.json")
    
    # Notify completion
    import subprocess
    stats = f"{len(duplicates)} duplicates, {issues['missing_coordinates']} missing coords"
    subprocess.run([
        '/home/miko/scripts/claude/notify.sh', 
        'complete', 
        f'Spot verification complete: {stats}'
    ])
    
    conn.close()

if __name__ == "__main__":
    main()