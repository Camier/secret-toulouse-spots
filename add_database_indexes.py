#!/usr/bin/env python3
"""
Add database indexes for improved query performance
"""

import sqlite3
import time
from pathlib import Path

def add_indexes(db_path="hidden_spots.db"):
    """Add performance indexes to the spots database"""
    
    if not Path(db_path).exists():
        print(f"❌ Database {db_path} not found!")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check existing indexes
    print("🔍 Checking existing indexes...")
    cursor.execute("""
        SELECT name, sql FROM sqlite_master 
        WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
    """)
    existing_indexes = cursor.fetchall()
    
    if existing_indexes:
        print(f"📊 Found {len(existing_indexes)} existing indexes:")
        for idx_name, idx_sql in existing_indexes:
            print(f"  - {idx_name}")
    else:
        print("📊 No custom indexes found")
    
    # Indexes to create
    indexes = [
        # Spatial index for coordinate queries
        ("idx_spots_coordinates", "CREATE INDEX IF NOT EXISTS idx_spots_coordinates ON spots(latitude, longitude)"),
        
        # Index for source-based queries
        ("idx_spots_source", "CREATE INDEX IF NOT EXISTS idx_spots_source ON spots(source)"),
        
        # Index for date-based queries
        ("idx_spots_scraped_at", "CREATE INDEX IF NOT EXISTS idx_spots_scraped_at ON spots(scraped_at)"),
        
        # Composite index for source and date
        ("idx_spots_source_date", "CREATE INDEX IF NOT EXISTS idx_spots_source_date ON spots(source, scraped_at)"),
        
        # Index for location type filtering
        ("idx_spots_location_type", "CREATE INDEX IF NOT EXISTS idx_spots_location_type ON spots(location_type)"),
        
        # Index for hidden/visibility filtering
        ("idx_spots_visibility", "CREATE INDEX IF NOT EXISTS idx_spots_visibility ON spots(is_hidden, visibility)"),
    ]
    
    print("\n🚀 Creating performance indexes...")
    
    for idx_name, idx_sql in indexes:
        try:
            print(f"  Creating {idx_name}...", end="", flush=True)
            start_time = time.time()
            cursor.execute(idx_sql)
            elapsed = time.time() - start_time
            print(f" ✅ ({elapsed:.2f}s)")
        except sqlite3.Error as e:
            print(f" ❌ Error: {e}")
    
    # Analyze query performance before and after
    print("\n📈 Testing query performance...")
    
    test_queries = [
        ("Coordinate range query", """
            SELECT COUNT(*) FROM spots 
            WHERE latitude BETWEEN 43.0 AND 44.0 
            AND longitude BETWEEN 0.5 AND 2.0
        """),
        ("Source filter query", """
            SELECT COUNT(*) FROM spots 
            WHERE source = 'osm'
        """),
        ("Recent spots query", """
            SELECT COUNT(*) FROM spots 
            WHERE scraped_at > date('now', '-7 days')
        """),
    ]
    
    for query_name, query_sql in test_queries:
        try:
            # Explain query plan
            cursor.execute(f"EXPLAIN QUERY PLAN {query_sql}")
            plan = cursor.fetchall()
            
            # Execute query with timing
            start_time = time.time()
            cursor.execute(query_sql)
            result = cursor.fetchone()
            elapsed = time.time() - start_time
            
            print(f"\n  {query_name}:")
            print(f"    Result: {result[0]} rows")
            print(f"    Time: {elapsed*1000:.2f}ms")
            print(f"    Plan: {' -> '.join([str(p[3]) for p in plan])}")
            
        except sqlite3.Error as e:
            print(f"    ❌ Error: {e}")
    
    # Optimize database
    print("\n🔧 Running database optimization...")
    cursor.execute("ANALYZE")
    cursor.execute("VACUUM")
    
    # Get database statistics
    cursor.execute("SELECT COUNT(*) FROM spots")
    total_spots = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT source) FROM spots")
    sources = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM spots WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
    with_coords = cursor.fetchone()[0]
    
    print(f"\n📊 Database Statistics:")
    print(f"  - Total spots: {total_spots:,}")
    print(f"  - Sources: {sources}")
    print(f"  - Spots with coordinates: {with_coords:,} ({with_coords/total_spots*100:.1f}%)")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Database optimization complete!")

if __name__ == "__main__":
    add_indexes()