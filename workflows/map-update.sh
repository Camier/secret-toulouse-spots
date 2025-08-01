#!/bin/bash
# Map Update Workflow - Updates web viewer with latest spots

echo "🗺️ Starting map update workflow..."

# Step 1: Export latest data from database
echo "📊 Exporting latest spots data..."
cd /home/miko/projects/secret-toulouse-spots
python3 -c "
import sqlite3
import json

conn = sqlite3.connect('hidden_spots.db')
cursor = conn.cursor()

# Get all spots with coordinates
cursor.execute('''
    SELECT * FROM spots 
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    ORDER BY is_hidden DESC, discovered_date DESC
''')

columns = [desc[0] for desc in cursor.description]
spots = []

for row in cursor.fetchall():
    spot = dict(zip(columns, row))
    spots.append(spot)

# Export to JSON for web viewer
with open('hidden_spots_export.json', 'w', encoding='utf-8') as f:
    json.dump(spots, f, ensure_ascii=False, indent=2)

conn.close()

print(f'✅ Exported {len(spots)} spots to hidden_spots_export.json')
"

# Step 2: Generate updated statistics
echo "📈 Generating statistics..."
TOTAL_SPOTS=$(sqlite3 hidden_spots.db "SELECT COUNT(*) FROM spots;")
HIDDEN_SPOTS=$(sqlite3 hidden_spots.db "SELECT COUNT(*) FROM spots WHERE is_hidden = 1;")
WITH_COORDS=$(sqlite3 hidden_spots.db "SELECT COUNT(*) FROM spots WHERE latitude IS NOT NULL;")

# Step 3: Update README with latest stats
echo "📝 Updating README..."
sed -i "s/Total Locations: [0-9]*/Total Locations: $TOTAL_SPOTS/" README.md
sed -i "s/Secret\/Hidden Spots: [0-9]*/Secret\/Hidden Spots: $HIDDEN_SPOTS/" README.md
sed -i "s/GPS Coordinates: [0-9]*+/GPS Coordinates: $WITH_COORDS/" README.md

# Step 4: Start web server if not running
if ! pgrep -f "http.server 8000" > /dev/null; then
    echo "🌐 Starting web server..."
    python3 -m http.server 8000 > /dev/null 2>&1 &
    sleep 2
fi

# Step 5: Open map in browser
echo "🌍 Opening updated map..."
xdg-open "http://localhost:8000/web_viewer.html" 2>/dev/null || \
    echo "Visit http://localhost:8000/web_viewer.html to view the map"

echo "✅ Map update complete!"
echo "   Total spots: $TOTAL_SPOTS"
echo "   Hidden spots: $HIDDEN_SPOTS"
echo "   With coordinates: $WITH_COORDS"

# Step 6: Log to memory
~/scripts/claude/notify.sh complete "Map updated: $TOTAL_SPOTS spots ($HIDDEN_SPOTS hidden, $WITH_COORDS mapped)"