#!/usr/bin/env python3
"""Visualize discovered spots around Toulouse on a map"""

import sqlite3
import folium
from math import radians, cos, sin, asin, sqrt

def haversine_distance(lat1, lng1, lat2, lng2):
    """Calculate distance in km between two points"""
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * asin(sqrt(a))
    return c * 6371

# Toulouse center
toulouse_lat = 43.6047
toulouse_lng = 1.4442
radius_km = 200

# Create map centered on Toulouse
map_toulouse = folium.Map(
    location=[toulouse_lat, toulouse_lng],
    zoom_start=8,
    tiles='OpenStreetMap'
)

# Add Toulouse marker
folium.Marker(
    [toulouse_lat, toulouse_lng],
    popup="<b>Toulouse</b><br>Search Center",
    tooltip="Toulouse",
    icon=folium.Icon(color='red', icon='star')
).add_to(map_toulouse)

# Add 200km radius circle
folium.Circle(
    location=[toulouse_lat, toulouse_lng],
    radius=radius_km * 1000,  # Convert to meters
    popup="200km search perimeter",
    color='blue',
    fill=True,
    fillOpacity=0.1
).add_to(map_toulouse)

# Get locations from database
conn = sqlite3.connect('../hidden_spots.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT DISTINCT extracted_name, latitude, longitude, source, is_hidden
    FROM scraped_locations 
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    ORDER BY source, extracted_name
""")

locations = cursor.fetchall()
conn.close()

# Add markers for each location
stats = {'total': 0, 'within': 0, 'hidden': 0}

for name, lat, lng, source, is_hidden in locations:
    distance = haversine_distance(toulouse_lat, toulouse_lng, lat, lng)
    
    # Determine marker color and icon
    if distance <= radius_km:
        color = 'green' if is_hidden else 'blue'
        stats['within'] += 1
    else:
        color = 'gray'
    
    if is_hidden:
        icon = 'key'
        stats['hidden'] += 1
    else:
        icon = 'info-sign'
    
    stats['total'] += 1
    
    # Create popup text
    popup_text = f"""
    <b>{name}</b><br>
    Source: {source}<br>
    Distance: {distance:.1f}km<br>
    {'🗝️ Hidden spot' if is_hidden else '📍 Public spot'}
    """
    
    # Add marker
    folium.Marker(
        [lat, lng],
        popup=popup_text,
        tooltip=f"{name} ({distance:.0f}km)",
        icon=folium.Icon(color=color, icon=icon)
    ).add_to(map_toulouse)

# Add legend
legend_html = f"""
<div style="position: fixed; 
     bottom: 50px; left: 50px; width: 250px; height: 150px; 
     background-color: white; border:2px solid grey; z-index:9999; 
     font-size:14px; padding: 10px">
<h4>Toulouse Area Spots</h4>
<p>⭐ Toulouse (center)</p>
<p>🟢 Hidden spots within 200km: {stats['hidden']}</p>
<p>🔵 Public spots within 200km: {stats['within'] - stats['hidden']}</p>
<p>⚫ Spots outside perimeter: {stats['total'] - stats['within']}</p>
<p><b>Total locations: {stats['total']}</b></p>
</div>
"""

map_toulouse.get_root().html.add_child(folium.Element(legend_html))

# Save map
map_toulouse.save('toulouse_spots_map.html')

print(f"\n🗺️ Map created: toulouse_spots_map.html")
print(f"\n📊 Statistics:")
print(f"   Total locations: {stats['total']}")
print(f"   Within 200km: {stats['within']}")
print(f"   Hidden spots: {stats['hidden']}")
print(f"   Outside perimeter: {stats['total'] - stats['within']}")

# Show locations within perimeter
print(f"\n📍 Locations within 200km of Toulouse:")
for name, lat, lng, source, is_hidden in locations:
    distance = haversine_distance(toulouse_lat, toulouse_lng, lat, lng)
    if distance <= radius_km:
        spot_type = "Hidden" if is_hidden else "Public"
        print(f"   - {name} ({distance:.1f}km) - {spot_type} - via {source}")