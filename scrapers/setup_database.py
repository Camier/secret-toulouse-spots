#!/usr/bin/env python3
"""Setup SQLite database for storing scraped locations"""

import sqlite3
from datetime import datetime
import os

def create_database():
    """Create SQLite database with tables for scraped locations"""
    
    # Create database directory if it doesn't exist
    db_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(db_dir, 'hidden_spots.db')
    
    print(f"📊 Creating SQLite database at: {db_path}")
    
    # Connect to database (creates if doesn't exist)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create scraped_locations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraped_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_url TEXT,
            raw_text TEXT,
            extracted_name TEXT,
            latitude REAL,
            longitude REAL,
            location_type TEXT,
            activities TEXT,
            is_hidden BOOLEAN DEFAULT 0,
            mentions_count INTEGER DEFAULT 1,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT
        )
    ''')
    
    # Create unique_spots table (deduplicated locations)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS unique_spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            type TEXT NOT NULL,
            activities TEXT,
            secrecy_level TEXT,
            total_mentions INTEGER DEFAULT 1,
            sources TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified BOOLEAN DEFAULT 0
        )
    ''')
    
    # Create forum_posts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forum_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            forum_name TEXT NOT NULL,
            post_url TEXT UNIQUE,
            author TEXT,
            post_date TIMESTAMP,
            content TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create instagram_posts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS instagram_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT UNIQUE,
            username TEXT,
            caption TEXT,
            hashtags TEXT,
            location_name TEXT,
            latitude REAL,
            longitude REAL,
            post_date TIMESTAMP,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indices for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_latitude_longitude ON scraped_locations(latitude, longitude)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_extracted_name ON scraped_locations(extracted_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_unique_spots_coords ON unique_spots(latitude, longitude)')
    
    # Commit changes
    conn.commit()
    
    print("✅ Database created successfully!")
    print("\n📋 Tables created:")
    print("  - scraped_locations: Raw scraped data")
    print("  - unique_spots: Deduplicated hidden spots")
    print("  - forum_posts: Forum post archive")
    print("  - instagram_posts: Instagram post data")
    
    # Show table schemas
    print("\n📊 Table schemas:")
    tables = ['scraped_locations', 'unique_spots', 'forum_posts', 'instagram_posts']
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        print(f"\n{table}:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
    
    conn.close()
    
    return db_path

def test_database(db_path):
    """Test database with sample data"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Insert test location
    cursor.execute('''
        INSERT INTO scraped_locations 
        (source, raw_text, extracted_name, latitude, longitude, location_type, activities, is_hidden)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        'test',
        'Test data for database setup',
        'Cascade Secrète de Test',
        44.1234,
        3.5678,
        'waterfall',
        'baignade,randonnée',
        1
    ))
    
    conn.commit()
    
    # Query test
    cursor.execute('SELECT COUNT(*) FROM scraped_locations')
    count = cursor.fetchone()[0]
    print(f"\n✅ Database test successful! {count} test record(s) inserted.")
    
    conn.close()

if __name__ == "__main__":
    db_path = create_database()
    test_database(db_path)