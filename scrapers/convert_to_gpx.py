#!/usr/bin/env python3
"""Convert spots CSV to GPX format for hiking apps"""

import csv
from datetime import datetime

import gpxpy
import gpxpy.gpx

# Create GPX object
gpx = gpxpy.gpx.GPX()

# Add metadata
gpx.name = "Secret Toulouse Spots"
gpx.description = "Hidden outdoor locations discovered near Toulouse"
gpx.author_name = "Secret Spots Discovery"
gpx.time = datetime.now()

# Read CSV and create waypoints
with open("../spots_coordinates.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["latitude"] and row["longitude"]:
            try:
                # Create waypoint
                wpt = gpxpy.gpx.GPXWaypoint(
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    name=row["name"],
                    description=f"{row['type']} - {row['activities']}",
                )

                # Add symbol based on type
                if (
                    "water" in row["type"].lower()
                    or "swimming" in row["activities"].lower()
                ):
                    wpt.symbol = "Swimming Area"
                elif (
                    "hot" in row["type"].lower()
                    or "thermal" in row["activities"].lower()
                ):
                    wpt.symbol = "Hot Spring"
                elif "cave" in row["type"].lower():
                    wpt.symbol = "Cave"
                elif (
                    "urbex" in row["type"].lower() or "abandoned" in row["type"].lower()
                ):
                    wpt.symbol = "Building"
                else:
                    wpt.symbol = "Scenic Area"

                gpx.waypoints.append(wpt)

            except ValueError as e:
                print(f"Skipping {row['name']}: {e}")

# Save GPX file
with open("../hidden_spots.gpx", "w", encoding="utf-8") as f:
    f.write(gpx.to_xml())

print(f"✅ GPX file created: hidden_spots.gpx")
print(f"📍 Total waypoints: {len(gpx.waypoints)}")
print("\n🎯 Import instructions:")
print("1. Copy hidden_spots.gpx to your phone")
print("2. Open in: OsmAnd, Organic Maps, Gaia GPS, or AllTrails")
print("3. Waypoints will appear as bookmarks/favorites")
