"""
Map Visualization Performance Code
Challenge: Rendering 3000+ markers on Leaflet map without browser freezing
"""

# Current implementation in enhanced-map.html JavaScript
var map = L.map('map').setView([43.6047, 1.4442], 10);

// Render all spots as individual markers
spotsData.forEach(function(spot) {
    var icon = getIconForType(spot.location_type);
    var marker = L.marker([spot.lat, spot.lng], {icon: icon})
        .bindPopup(createPopupContent(spot));
    
    // Add to appropriate layer group
    if (spot.source.startsWith('osm_')) {
        osmLayer.addLayer(marker);
    } else if (spot.source === 'reddit') {
        redditLayer.addLayer(marker);
    } else if (spot.source === 'instagram') {
        instagramLayer.addLayer(marker);
    } else {
        miscLayer.addLayer(marker);
    }
});

// Python code that generates the data
def generate_map_data():
    """Generate map data JSON file from database"""
    conn = sqlite3.connect("hidden_spots.db")
    cursor = conn.cursor()
    
    # Get all spots with coordinates
    cursor.execute("""
        SELECT id, source, extracted_name, latitude, longitude, 
               location_type, activities, is_hidden, raw_text, metadata
        FROM spots
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """)
    
    spots = cursor.fetchall()
    
    # Convert to JSON (3000+ spots)
    spots_data = []
    for spot in spots:
        spot_obj = {
            "id": spot[0],
            "name": spot[2] or f"Spot from {spot[1]}",
            "lat": spot[3],
            "lng": spot[4],
            "source": spot[1],
            "location_type": spot[5] or "unknown",
            "activities": spot[6] or "",
            "is_hidden": spot[7],
            "description": spot[8][:200] if spot[8] else "",
            "metadata": json.loads(spot[9]) if spot[9] else {}
        }
        spots_data.append(spot_obj)
    
    # Write to JSON file
    with open("map_data.json", "w", encoding="utf-8") as f:
        json.dump(spots_data, f, ensure_ascii=False, indent=2)
    
    return len(spots_data)