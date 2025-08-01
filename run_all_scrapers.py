#!/usr/bin/env python3
"""
Master script to run all scrapers and collect hidden spots data
"""

import subprocess
import sys
import sqlite3
from datetime import datetime
import json

def run_scraper(scraper_path, name):
    """Run a scraper and return success status"""
    print(f"\n{'='*60}")
    print(f"🚀 Running {name}...")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, scraper_path], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {name} completed successfully")
            print(result.stdout)
            return True
        else:
            print(f"❌ {name} failed with error:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Failed to run {name}: {e}")
        return False

def get_database_stats():
    """Get current database statistics"""
    conn = sqlite3.connect('hidden_spots.db')
    cursor = conn.cursor()
    
    # Total spots
    cursor.execute("SELECT COUNT(*) FROM spots")
    total = cursor.fetchone()[0]
    
    # Spots with coordinates
    cursor.execute("SELECT COUNT(*) FROM spots WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    with_coords = cursor.fetchone()[0]
    
    # Hidden spots
    cursor.execute("SELECT COUNT(*) FROM spots WHERE is_hidden = 1")
    hidden = cursor.fetchone()[0]
    
    # Spots by source
    cursor.execute("""
        SELECT source, COUNT(*) as count 
        FROM spots 
        GROUP BY source 
        ORDER BY count DESC
    """)
    by_source = cursor.fetchall()
    
    # Spots by location type
    cursor.execute("""
        SELECT location_type, COUNT(*) as count 
        FROM spots 
        GROUP BY location_type 
        ORDER BY count DESC
    """)
    by_type = cursor.fetchall()
    
    conn.close()
    
    return {
        'total': total,
        'with_coords': with_coords,
        'hidden': hidden,
        'by_source': by_source,
        'by_type': by_type
    }

def main():
    print("🔍 Secret Toulouse Spots - Master Scraper")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get initial stats
    print("\n📊 Initial database stats:")
    initial_stats = get_database_stats()
    print(f"   Total spots: {initial_stats['total']}")
    print(f"   With coordinates: {initial_stats['with_coords']}")
    
    # List of scrapers to run
    scrapers = [
        ('scrapers/geocaching_scraper.py', 'Geocaching Scraper'),
        ('scrapers/reddit_enhanced_scraper.py', 'Reddit Enhanced Scraper'),
        ('scrapers/tourism_sites_scraper.py', 'Tourism Sites Scraper'),
        ('scrapers/instagram_scraper.py', 'Instagram Hashtag Scraper'),
    ]
    
    # Run each scraper
    successful = []
    failed = []
    
    for scraper_path, name in scrapers:
        if run_scraper(scraper_path, name):
            successful.append(name)
        else:
            failed.append(name)
    
    # Get final stats
    print("\n📊 Final database stats:")
    final_stats = get_database_stats()
    print(f"   Total spots: {final_stats['total']} (+{final_stats['total'] - initial_stats['total']})")
    print(f"   With coordinates: {final_stats['with_coords']} (+{final_stats['with_coords'] - initial_stats['with_coords']})")
    print(f"   Hidden spots: {final_stats['hidden']}")
    
    print("\n📈 Spots by source:")
    for source, count in final_stats['by_source']:
        print(f"   {source}: {count}")
    
    print("\n🏷️ Spots by type:")
    for loc_type, count in final_stats['by_type']:
        print(f"   {loc_type}: {count}")
    
    # Summary
    print(f"\n{'='*60}")
    print("🏁 SCRAPING COMPLETE")
    print(f"{'='*60}")
    print(f"✅ Successful scrapers: {len(successful)}")
    for s in successful:
        print(f"   - {s}")
    
    if failed:
        print(f"\n❌ Failed scrapers: {len(failed)}")
        for f in failed:
            print(f"   - {f}")
    
    print(f"\n📊 Total new spots added: {final_stats['total'] - initial_stats['total']}")
    print(f"🎯 Success rate: {len(successful)}/{len(scrapers)} ({len(successful)/len(scrapers)*100:.0f}%)")
    
    # Run standardization
    print("\n🔧 Running data standardization...")
    try:
        result = subprocess.run([sys.executable, 'standardize_data.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Data standardization completed")
            print(result.stdout)
        else:
            print("❌ Data standardization failed")
            print(result.stderr)
    except Exception as e:
        print(f"❌ Failed to run standardization: {e}")
    
    # Export final data
    print("\n📤 Exporting final data...")
    try:
        result = subprocess.run([sys.executable, 'export_all_spots.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Data export completed")
            print(result.stdout)
        else:
            print("❌ Data export failed")
            print(result.stderr)
    except Exception as e:
        print(f"❌ Failed to export data: {e}")
    
    print(f"\n✨ All done! Check 'all_spots_export.json' for complete data")
    print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()