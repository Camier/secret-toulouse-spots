#!/usr/bin/env python3
"""
Generate a comprehensive data quality report for the secret spots database
"""

import sqlite3
from collections import Counter
from datetime import datetime


def generate_report():
    """Generate comprehensive data quality report"""
    conn = sqlite3.connect("hidden_spots.db")
    cursor = conn.cursor()

    print("📊 SECRET TOULOUSE SPOTS - DATA QUALITY REPORT")
    print(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. Overall Statistics
    cursor.execute(
        """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 ELSE 0 END) as with_coords,
            SUM(CASE WHEN latitude IS NULL OR longitude IS NULL THEN 1 ELSE 0 END) as without_coords,
            SUM(CASE WHEN is_hidden = 1 THEN 1 ELSE 0 END) as hidden,
            COUNT(DISTINCT source) as sources,
            COUNT(DISTINCT location_type) as types
        FROM spots
    """
    )

    stats = cursor.fetchone()
    print("\n📈 OVERALL STATISTICS")
    print(f"Total spots: {stats[0]}")
    print(f"With coordinates: {stats[1]} ({stats[1]/stats[0]*100:.1f}%)")
    print(f"Without coordinates: {stats[2]} ({stats[2]/stats[0]*100:.1f}%)")
    print(f"Hidden/secret spots: {stats[3]} ({stats[3]/stats[0]*100:.1f}%)")
    print(f"Data sources: {stats[4]}")
    print(f"Location types: {stats[5]}")

    # 2. Data Sources Breakdown
    print("\n📍 BY DATA SOURCE")
    cursor.execute(
        """
        SELECT 
            source,
            COUNT(*) as total,
            SUM(CASE WHEN latitude IS NOT NULL THEN 1 ELSE 0 END) as with_coords,
            SUM(CASE WHEN is_hidden = 1 THEN 1 ELSE 0 END) as hidden
        FROM spots
        GROUP BY source
        ORDER BY total DESC
    """
    )

    sources = cursor.fetchall()
    for source, total, with_coords, hidden in sources:
        coord_pct = with_coords / total * 100 if total > 0 else 0
        hidden_pct = hidden / total * 100 if total > 0 else 0
        print(
            f"  {source}: {total} spots ({coord_pct:.0f}% with coords, {hidden_pct:.0f}% hidden)"
        )

    # 3. Location Types
    print("\n🏷️ BY LOCATION TYPE")
    cursor.execute(
        """
        SELECT 
            location_type,
            COUNT(*) as total,
            SUM(CASE WHEN latitude IS NOT NULL THEN 1 ELSE 0 END) as with_coords
        FROM spots
        GROUP BY location_type
        ORDER BY total DESC
    """
    )

    types = cursor.fetchall()
    for loc_type, total, with_coords in types:
        coord_pct = with_coords / total * 100 if total > 0 else 0
        print(f"  {loc_type}: {total} spots ({coord_pct:.0f}% with coords)")

    # 4. Data Quality Issues
    print("\n⚠️ DATA QUALITY ISSUES")

    # Short names
    cursor.execute("SELECT COUNT(*) FROM spots WHERE length(extracted_name) < 10")
    short_names = cursor.fetchone()[0]
    print(f"  Short names (<10 chars): {short_names}")

    # Generic names
    cursor.execute(
        """
        SELECT COUNT(*) FROM spots 
        WHERE extracted_name IN ('Affichage', 'Endroit', 'Grotte', 'Spot', 'Location')
    """
    )
    generic_names = cursor.fetchone()[0]
    print(f"  Generic names: {generic_names}")

    # Missing activities
    cursor.execute(
        """
        SELECT COUNT(*) FROM spots 
        WHERE activities IS NULL OR activities = '' OR activities = 'exploration'
    """
    )
    no_activities = cursor.fetchone()[0]
    print(f"  Missing/generic activities: {no_activities}")

    # Duplicates check
    cursor.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT extracted_name, latitude, longitude, COUNT(*) as cnt
            FROM spots
            WHERE latitude IS NOT NULL
            GROUP BY extracted_name, ROUND(latitude, 4), ROUND(longitude, 4)
            HAVING cnt > 1
        )
    """
    )
    duplicate_groups = cursor.fetchone()[0]
    print(f"  Potential duplicate groups: {duplicate_groups}")

    # 5. Geographic Distribution
    print("\n🗺️ GEOGRAPHIC DISTRIBUTION")
    cursor.execute(
        """
        SELECT 
            CASE 
                WHEN json_extract(metadata, '$.distance_from_toulouse_km') < 20 THEN '< 20km'
                WHEN json_extract(metadata, '$.distance_from_toulouse_km') < 50 THEN '20-50km'
                WHEN json_extract(metadata, '$.distance_from_toulouse_km') < 100 THEN '50-100km'
                ELSE '> 100km'
            END as distance_range,
            COUNT(*) as count
        FROM spots
        WHERE json_extract(metadata, '$.distance_from_toulouse_km') IS NOT NULL
        GROUP BY distance_range
        ORDER BY 
            CASE distance_range
                WHEN '< 20km' THEN 1
                WHEN '20-50km' THEN 2
                WHEN '50-100km' THEN 3
                ELSE 4
            END
    """
    )

    distances = cursor.fetchall()
    for range_name, count in distances:
        print(f"  {range_name}: {count} spots")

    # 6. Activity Analysis
    print("\n🏃 ACTIVITY DISTRIBUTION")
    cursor.execute("SELECT activities FROM spots WHERE activities IS NOT NULL")
    all_activities = cursor.fetchall()

    activity_counter = Counter()
    for (activities,) in all_activities:
        if activities:
            for activity in activities.split(", "):
                activity_counter[activity.strip()] += 1

    for activity, count in activity_counter.most_common(10):
        print(f"  {activity}: {count} spots")

    # 7. Recent Additions
    print("\n📅 RECENT ADDITIONS (Last 7 days)")
    cursor.execute(
        """
        SELECT 
            DATE(scraped_at) as date,
            COUNT(*) as count,
            GROUP_CONCAT(DISTINCT source) as sources
        FROM spots
        WHERE scraped_at > datetime('now', '-7 days')
        GROUP BY DATE(scraped_at)
        ORDER BY date DESC
    """
    )

    recent = cursor.fetchall()
    if recent:
        for date, count, sources in recent:
            print(f"  {date}: {count} spots from {sources}")
    else:
        print("  No additions in the last 7 days")

    # 8. Recommendations
    print("\n💡 RECOMMENDATIONS")

    recommendations = []

    if stats[2] > stats[0] * 0.3:  # More than 30% without coords
        recommendations.append(
            f"High priority: {stats[2]} spots ({stats[2]/stats[0]*100:.0f}%) missing coordinates - run geocoding"
        )

    if short_names > 5:
        recommendations.append(f"Fix {short_names} spots with short names")

    if duplicate_groups > 5:
        recommendations.append(
            f"Review and merge {duplicate_groups} potential duplicate groups"
        )

    if no_activities > stats[0] * 0.2:  # More than 20% without activities
        recommendations.append(
            f"Enrich {no_activities} spots with proper activity tags"
        )

    # Check for missing sources
    missing_sources = []
    source_names = [s[0] for s in sources]
    if not any("facebook" in s for s in source_names):
        missing_sources.append("Facebook")
    if not any("osm" in s for s in source_names):
        missing_sources.append("OpenStreetMap")
    if not any("wikiloc" in s for s in source_names):
        missing_sources.append("Wikiloc")

    if missing_sources:
        recommendations.append(f"Add scrapers for: {', '.join(missing_sources)}")

    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")

    # 9. Data Completeness Score
    print("\n🎯 DATA QUALITY SCORE")

    # Calculate scores
    coord_score = stats[1] / stats[0] * 100
    name_score = (stats[0] - short_names - generic_names) / stats[0] * 100
    activity_score = (stats[0] - no_activities) / stats[0] * 100

    overall_score = (coord_score + name_score + activity_score) / 3

    print(f"  Coordinate completeness: {coord_score:.1f}%")
    print(f"  Name quality: {name_score:.1f}%")
    print(f"  Activity tagging: {activity_score:.1f}%")
    print(f"  OVERALL SCORE: {overall_score:.1f}%")

    if overall_score >= 80:
        print("  Grade: A - Excellent data quality! 🌟")
    elif overall_score >= 70:
        print("  Grade: B - Good data quality 👍")
    elif overall_score >= 60:
        print("  Grade: C - Acceptable, needs improvement 📈")
    else:
        print("  Grade: D - Poor quality, immediate action needed ⚠️")

    conn.close()


if __name__ == "__main__":
    generate_report()
