#!/usr/bin/env python3
"""
Create a proper spots table for all scraped data
"""

import sqlite3


def create_spots_table():
    conn = sqlite3.connect("hidden_spots.db")
    cursor = conn.cursor()

    # Create the new spots table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_url TEXT,
            raw_text TEXT,
            extracted_name TEXT,
            latitude REAL,
            longitude REAL,
            location_type TEXT,
            activities TEXT,
            is_hidden INTEGER DEFAULT 0,
            mentions_count INTEGER DEFAULT 1,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            discovered_date TIMESTAMP,
            discovery_snippet TEXT,
            metadata TEXT
        )
    """
    )

    # Create indexes
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_spots_coords ON spots(latitude, longitude)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_spots_name ON spots(extracted_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_spots_source ON spots(source)")

    conn.commit()

    # Check if we need to migrate data
    cursor.execute("SELECT COUNT(*) FROM unique_spots")
    unique_count = cursor.fetchone()[0]

    if unique_count > 0:
        print(f"Found {unique_count} spots in unique_spots table")

        # Migrate data
        cursor.execute(
            """
            INSERT INTO spots (
                extracted_name, latitude, longitude, location_type, 
                activities, is_hidden, scraped_at, source
            )
            SELECT 
                name, latitude, longitude, type,
                activities, 
                CASE WHEN secrecy_level = 'secret' THEN 1 ELSE 0 END,
                first_seen,
                sources
            FROM unique_spots
        """
        )

        migrated = cursor.rowcount
        print(f"Migrated {migrated} spots to new table")

    conn.commit()
    conn.close()

    print("✅ Spots table created successfully!")


if __name__ == "__main__":
    create_spots_table()
