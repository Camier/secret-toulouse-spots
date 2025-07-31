#!/usr/bin/env python3
"""
Main scraper for French outdoor hidden spots
Combines CampToCamp forum scraping and Instagram mining
"""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
import time

# Import our scrapers
from test_camptocamp_real import scrape_camptocamp_outings, analyze_database
try:
    from instagram_scraper_secure import SecureInstagramScraper as FrenchOutdoorInstagramScraper
except ImportError:
    # Fallback to original if secure version not available
    from instagram_scraper_final import FrenchOutdoorInstagramScraper

class HiddenSpotsAggregator:
    """Main class to orchestrate all scrapers"""
    
    def __init__(self):
        self.db_path = "hidden_spots.db"
        self.ensure_database()
    
    def ensure_database(self):
        """Make sure database exists with proper schema"""
        # Database is already created by setup_database.py
        # Just verify it exists
        if not Path(self.db_path).exists():
            print("❌ Database not found! Run setup_database.py first")
            exit(1)
    
    def run_camptocamp_scraper(self):
        """Run CampToCamp forum scraper"""
        print("\n" + "="*60)
        print("🏔️ CAMPTOCAMP SCRAPER")
        print("="*60)
        
        # This function handles its own database saving
        outings = scrape_camptocamp_outings()
        
        return len(outings) if outings else 0
    
    def run_instagram_scraper(self):
        """Run Instagram scraper"""
        print("\n" + "="*60)
        print("📸 INSTAGRAM SCRAPER")
        print("="*60)
        
        scraper = FrenchOutdoorInstagramScraper()
        
        if scraper.login():
            posts = scraper.run_full_scrape()
            return len(posts)
        else:
            print("❌ Instagram authentication failed")
            return 0
    
    def generate_summary_report(self):
        """Generate a summary of all collected data"""
        print("\n" + "="*60)
        print("📊 FINAL SUMMARY REPORT")
        print("="*60)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total posts from all sources
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM forum_posts) as forum_count,
                (SELECT COUNT(*) FROM instagram_posts) as instagram_count
        """)
        forum_count, instagram_count = cursor.fetchone()
        
        print(f"\n📝 Total Content Collected:")
        print(f"   Forum posts: {forum_count}")
        print(f"   Instagram posts: {instagram_count}")
        print(f"   Total: {forum_count + instagram_count}")
        
        # Geotagged locations
        cursor.execute("""
            SELECT COUNT(*), source 
            FROM scraped_locations 
            WHERE latitude IS NOT NULL 
            GROUP BY source
        """)
        
        print(f"\n📍 Geotagged Locations by Source:")
        for count, source in cursor.fetchall():
            print(f"   {source}: {count} locations")
        
        # Hidden spots
        cursor.execute("""
            SELECT COUNT(*) 
            FROM scraped_locations 
            WHERE is_hidden = 1
        """)
        hidden_count = cursor.fetchone()[0]
        print(f"\n🗝️ Hidden spots identified: {hidden_count}")
        
        # Top locations
        cursor.execute("""
            SELECT extracted_name, latitude, longitude, source
            FROM scraped_locations 
            WHERE latitude IS NOT NULL 
            ORDER BY scraped_at DESC 
            LIMIT 10
        """)
        
        locations = cursor.fetchall()
        if locations:
            print("\n🏆 Latest Discovered Locations:")
            for name, lat, lng, source in locations:
                print(f"   - {name} ({lat:.4f}, {lng:.4f}) via {source}")
        
        # Save summary to file
        summary_file = "scraping_summary.txt"
        with open(summary_file, "w") as f:
            f.write(f"French Outdoor Hidden Spots - Scraping Summary\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"\nTotal Content:\n")
            f.write(f"- Forum posts: {forum_count}\n")
            f.write(f"- Instagram posts: {instagram_count}\n")
            f.write(f"- Hidden spots: {hidden_count}\n")
            f.write(f"\nGeotagged Locations: {len(locations)}\n")
            
            if locations:
                f.write("\nTop Locations:\n")
                for name, lat, lng, source in locations:
                    f.write(f"- {name} ({lat:.4f}, {lng:.4f}) via {source}\n")
        
        print(f"\n💾 Summary saved to: {summary_file}")
        
        conn.close()
    
    def export_for_weather_app(self):
        """Export data in format suitable for weather app integration"""
        print("\n🔄 Exporting data for weather app...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all geotagged locations
        cursor.execute("""
            SELECT DISTINCT 
                extracted_name as name,
                latitude,
                longitude,
                source,
                raw_text,
                is_hidden
            FROM scraped_locations 
            WHERE latitude IS NOT NULL 
            ORDER BY scraped_at DESC
        """)
        
        locations = cursor.fetchall()
        
        # Create export file
        export_data = {
            "generated_at": datetime.now().isoformat(),
            "total_locations": len(locations),
            "locations": []
        }
        
        for name, lat, lng, source, text, is_hidden in locations:
            # Determine location type based on text
            location_type = "unknown"
            if any(word in (text or "").lower() for word in ["cascade", "chute"]):
                location_type = "waterfall"
            elif any(word in (text or "").lower() for word in ["lac", "étang"]):
                location_type = "lake"
            elif any(word in (text or "").lower() for word in ["source", "fontaine"]):
                location_type = "spring"
            elif any(word in (text or "").lower() for word in ["baignade", "piscine naturelle"]):
                location_type = "swimming_spot"
            
            export_data["locations"].append({
                "name": name or f"Spot_{lat:.4f}_{lng:.4f}",
                "coordinates": {
                    "latitude": lat,
                    "longitude": lng
                },
                "type": location_type,
                "is_hidden": bool(is_hidden),
                "source": source,
                "description": (text[:200] + "...") if text and len(text) > 200 else text
            })
        
        # Save as JSON
        import json
        export_file = "hidden_spots_export.json"
        with open(export_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Exported {len(locations)} locations to: {export_file}")
        
        conn.close()
        
        return export_file

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Scrape French outdoor hidden spots")
    parser.add_argument("--camptocamp", action="store_true", help="Run only CampToCamp scraper")
    parser.add_argument("--instagram", action="store_true", help="Run only Instagram scraper")
    parser.add_argument("--export", action="store_true", help="Export data for weather app")
    args = parser.parse_args()
    
    aggregator = HiddenSpotsAggregator()
    
    # Determine what to run
    run_all = not (args.camptocamp or args.instagram or args.export)
    
    if run_all or args.camptocamp:
        aggregator.run_camptocamp_scraper()
        time.sleep(2)
    
    if run_all or args.instagram:
        aggregator.run_instagram_scraper()
        time.sleep(2)
    
    # Always show summary after scraping
    if run_all or args.camptocamp or args.instagram:
        aggregator.generate_summary_report()
    
    # Export if requested
    if run_all or args.export:
        aggregator.export_for_weather_app()
    
    print("\n✅ All operations completed!")

if __name__ == "__main__":
    main()