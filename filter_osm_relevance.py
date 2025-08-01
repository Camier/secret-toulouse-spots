#!/usr/bin/env python3
"""
Filter OpenStreetMap spots for relevance based on multiple criteria.
Reduces 3,181 OSM spots to only the most interesting and accessible ones.
"""

import sqlite3
import json
from datetime import datetime

def calculate_relevance_score(spot):
    """
    Calculate relevance score for an OSM spot based on multiple criteria.
    Higher score = more relevant/interesting
    """
    score = 0
    metadata = json.loads(spot['metadata']) if spot['metadata'] else {}
    osm_tags = metadata.get('osm_tags', {})
    
    # 1. Named vs unnamed (+3 for proper names, -2 for generic names)
    name = spot['extracted_name'] or ''
    if name and not any(generic in name.lower() for generic in ['non nommée', 'unnamed', 'sans nom']):
        score += 3
    elif 'non nommée' in name.lower():
        score -= 2
    
    # 2. Distance from Toulouse
    distance = metadata.get('distance_from_toulouse_km')
    if distance:
        if distance <= 20:
            score += 3  # Day trip distance
        elif distance <= 50:
            score += 2  # Easy weekend trip
        elif distance <= 100:
            score += 1  # Weekend trip
        else:
            score -= 1  # Far
    
    # 3. Accessibility (REVISED: difficult access = more secret/rare!)
    access = osm_tags.get('access', '')
    if access in ['private', 'no']:
        score += 2  # Private/restricted = more secret!
    elif access == 'permissive':
        score += 1  # Semi-private = interesting
    elif access in ['yes', 'public']:
        score -= 1  # Too easy/public = less interesting
    
    # 4. Interesting features from OSM tags
    interesting_tags = ['tourism', 'leisure', 'sport', 'historic', 'natural']
    for tag in interesting_tags:
        if tag in osm_tags and osm_tags[tag] not in ['no', 'none']:
            score += 2
    
    # 5. Description quality
    if osm_tags.get('description') or osm_tags.get('description:fr'):
        score += 2
    
    # 6. Type-specific scoring
    source = spot['source'] or ''
    if 'waterfall' in source:
        score += 2  # Waterfalls are inherently interesting
    elif 'cave' in source:
        score += 2  # Caves too
    elif 'ruins' in source:
        score += 2  # Historical ruins
    elif 'viewpoint' in source:
        if name and 'non nommée' not in name.lower():
            score += 1  # Named viewpoints only
        else:
            score -= 1  # Unnamed viewpoints less interesting
    elif 'spring' in source:
        # Springs need more criteria to be interesting
        if osm_tags.get('drinking_water') == 'yes':
            score += 2
        elif osm_tags.get('natural') == 'hot_spring':
            score += 3
        elif not name or 'non nommée' in name.lower():
            score -= 3  # Unnamed springs usually not interesting
    
    # 7. Elevation bonus for viewpoints
    if 'viewpoint' in source and osm_tags.get('ele'):
        try:
            elevation = float(osm_tags['ele'])
            if elevation > 500:
                score += 1
        except:
            pass
    
    # 8. Wikipedia/Wikidata bonus (indicates notability)
    if osm_tags.get('wikipedia') or osm_tags.get('wikidata'):
        score += 2
    
    # 9. Has amenities nearby (actually makes it LESS secret)
    if any(tag in osm_tags for tag in ['parking', 'toilets', 'picnic_site']):
        score -= 1  # Too developed = less secret
    
    # 10. Rarity indicators (NEW!)
    rarity_keywords = ['abandoned', 'disused', 'ruins', 'hidden', 'secret', 'cache', 'grotte', 'souterrain']
    description_text = (osm_tags.get('description', '') + ' ' + osm_tags.get('name', '')).lower()
    for keyword in rarity_keywords:
        if keyword in description_text:
            score += 2
    
    # 11. Difficulty indicators
    if osm_tags.get('climbing') == 'yes' or osm_tags.get('sac_scale'):
        score += 2  # Requires climbing/hiking = more adventurous
    if osm_tags.get('trail_visibility') in ['bad', 'horrible', 'no']:
        score += 2  # Hard to find = more secret!
    
    return score

def filter_osm_spots():
    """Main function to filter OSM spots by relevance"""
    conn = sqlite3.connect('hidden_spots.db')
    cursor = conn.cursor()
    
    print("🔍 Filtering OpenStreetMap spots for relevance...")
    
    # Get all OSM spots
    cursor.execute("""
        SELECT id, source, extracted_name, latitude, longitude, 
               location_type, activities, is_hidden, raw_text, metadata
        FROM spots
        WHERE source LIKE 'osm_%'
    """)
    
    osm_spots = cursor.fetchall()
    print(f"   Found {len(osm_spots)} OSM spots to evaluate")
    
    # Calculate scores and categorize
    high_relevance = []
    medium_relevance = []
    low_relevance = []
    
    score_distribution = {}
    
    for spot in osm_spots:
        spot_dict = {
            'id': spot[0],
            'source': spot[1],
            'extracted_name': spot[2],
            'latitude': spot[3],
            'longitude': spot[4],
            'location_type': spot[5],
            'activities': spot[6],
            'is_hidden': spot[7],
            'raw_text': spot[8],
            'metadata': spot[9]
        }
        
        score = calculate_relevance_score(spot_dict)
        
        # Update metadata with score
        metadata = json.loads(spot[9]) if spot[9] else {}
        metadata['relevance_score'] = score
        metadata['relevance_evaluated_at'] = datetime.now().isoformat()
        
        cursor.execute("""
            UPDATE spots 
            SET metadata = ?
            WHERE id = ?
        """, (json.dumps(metadata), spot[0]))
        
        # Categorize
        if score >= 5:
            high_relevance.append((spot[0], spot[2], score))
        elif score >= 3:
            medium_relevance.append((spot[0], spot[2], score))
        else:
            low_relevance.append((spot[0], spot[2], score))
        
        # Track score distribution
        score_distribution[score] = score_distribution.get(score, 0) + 1
    
    conn.commit()
    
    # Print results
    print(f"\n📊 Relevance Analysis Complete:")
    print(f"   High relevance (≥5): {len(high_relevance)} spots")
    print(f"   Medium relevance (3-4): {len(medium_relevance)} spots")
    print(f"   Low relevance (<3): {len(low_relevance)} spots")
    
    print(f"\n📈 Score Distribution:")
    for score in sorted(score_distribution.keys(), reverse=True):
        print(f"   Score {score:2d}: {'█' * min(50, score_distribution[score])} ({score_distribution[score]})")
    
    # Show examples from each category
    print(f"\n🌟 High Relevance Examples:")
    for id, name, score in high_relevance[:5]:
        print(f"   [{score}] {name}")
    
    print(f"\n📍 Medium Relevance Examples:")
    for id, name, score in medium_relevance[:5]:
        print(f"   [{score}] {name}")
    
    print(f"\n⚠️  Low Relevance Examples (consider removing):")
    for id, name, score in low_relevance[:5]:
        print(f"   [{score}] {name}")
    
    # Create filtered export
    print(f"\n💾 Creating filtered export...")
    
    # Export only high and medium relevance spots
    cursor.execute("""
        SELECT * FROM spots
        WHERE 
            (source LIKE 'osm_%' AND 
             CAST(json_extract(metadata, '$.relevance_score') AS INTEGER) >= 3)
            OR source NOT LIKE 'osm_%'
        ORDER BY 
            CASE 
                WHEN source LIKE 'osm_%' THEN CAST(json_extract(metadata, '$.relevance_score') AS INTEGER)
                ELSE 10 
            END DESC
    """)
    
    filtered_spots = []
    for row in cursor.fetchall():
        spot = {
            'id': row[0],
            'source': row[1],
            'source_url': row[2],
            'raw_text': row[3],
            'extracted_name': row[4],
            'latitude': row[5],
            'longitude': row[6],
            'location_type': row[7],
            'activities': row[8],
            'is_hidden': row[9],
            'mentions_count': row[10],
            'scraped_at': row[11],
            'discovered_date': row[12],
            'discovery_snippet': row[13],
            'metadata': row[14]
        }
        filtered_spots.append(spot)
    
    # Save filtered export
    with open('filtered_spots_high_relevance.json', 'w', encoding='utf-8') as f:
        json.dump(filtered_spots, f, ensure_ascii=False, indent=2)
    
    print(f"   Exported {len(filtered_spots)} spots to filtered_spots_high_relevance.json")
    print(f"   Reduced from {len(osm_spots)} OSM spots to {len(high_relevance) + len(medium_relevance)}")
    
    # Summary statistics
    total_original = cursor.execute("SELECT COUNT(*) FROM spots").fetchone()[0]
    total_filtered = len(filtered_spots)
    reduction = (1 - len(high_relevance + medium_relevance) / len(osm_spots)) * 100
    
    print(f"\n✅ Filtering Complete!")
    print(f"   Original total spots: {total_original}")
    print(f"   Filtered total spots: {total_filtered}")
    print(f"   OSM reduction: {reduction:.1f}%")
    print(f"   Removed {len(low_relevance)} low-relevance OSM spots")
    
    conn.close()

if __name__ == "__main__":
    filter_osm_spots()