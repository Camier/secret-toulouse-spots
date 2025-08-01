#!/usr/bin/env python3
"""
Export all spots from the database to JSON
"""

import json
import sqlite3


def export_spots():
    conn = sqlite3.connect("hidden_spots.db")
    cursor = conn.cursor()

    # Get all spots
    cursor.execute(
        """
        SELECT * FROM spots 
        ORDER BY is_hidden DESC, scraped_at DESC
    """
    )

    columns = [desc[0] for desc in cursor.description]
    spots = []

    for row in cursor.fetchall():
        spot = dict(zip(columns, row))
        spots.append(spot)

    # Export to JSON
    with open("all_spots_export.json", "w", encoding="utf-8") as f:
        json.dump(spots, f, ensure_ascii=False, indent=2)

    # Count statistics
    total = len(spots)
    with_coords = len([s for s in spots if s["latitude"] and s["longitude"]])
    hidden = len([s for s in spots if s["is_hidden"]])

    print(f"✅ Exported {total} spots")
    print(f"   With coordinates: {with_coords}")
    print(f"   Hidden/secret: {hidden}")
    print(f"   Without coordinates: {total - with_coords}")

    # Export with coordinates only
    spots_with_coords = [s for s in spots if s["latitude"] and s["longitude"]]
    with open("hidden_spots_export.json", "w", encoding="utf-8") as f:
        json.dump(spots_with_coords, f, ensure_ascii=False, indent=2)

    conn.close()


if __name__ == "__main__":
    export_spots()
