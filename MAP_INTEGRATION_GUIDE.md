# 🗺️ Map Integration Guide for Hidden Toulouse Spots

## 📊 Available Data Formats

### 1. CSV File (spots_coordinates.csv)
- **Format**: `name,latitude,longitude,type,activities`
- **Records**: 67 locations with GPS coordinates
- **Best for**: Google Maps, GPX converters, spreadsheet apps

### 2. JSON Export (hidden_spots_export.json)
- **Format**: Complete metadata for all 43 hidden spots
- **Includes**: GPS, descriptions, source, discovery date
- **Best for**: Custom web apps, advanced filtering

### 3. SQLite Database (hidden_spots.db)
- **Format**: Full relational database
- **Features**: Complex queries, relationship data
- **Best for**: Desktop GIS applications, custom tools

## 🎯 Integration Methods

### Method 1: Google My Maps (Easiest)
```
1. Go to https://mymaps.google.com
2. Create new map: "Hidden Toulouse Spots"
3. Click "Import" → Upload spots_coordinates.csv
4. Map columns:
   - Latitude → Latitude field
   - Longitude → Longitude field  
   - Name → Title
5. Style by type:
   - 💧 Blue markers for water spots
   - 🔥 Red markers for hot springs
   - 🏚️ Gray markers for urbex
   - 🟢 Green markers for hidden spots
```

### Method 2: Folium Interactive Map (Already Built!)
```bash
cd ~/projects/secret-toulouse-spots/scrapers
python visualize_toulouse_spots.py
# Opens toulouse_spots_map.html in browser
```

Features:
- Color-coded markers (green=hidden, blue=public)
- Distance from Toulouse calculated
- Interactive popups with details
- 200km search radius shown

### Method 3: GPX for Hiking Apps
```python
# Create convert_to_gpx.py
import csv
import gpxpy
import gpxpy.gpx

gpx = gpxpy.gpx.GPX()

with open('spots_coordinates.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['latitude'] and row['longitude']:
            wpt = gpxpy.gpx.GPXWaypoint(
                latitude=float(row['latitude']),
                longitude=float(row['longitude']),
                name=row['name'],
                description=f"{row['type']} - {row['activities']}"
            )
            gpx.waypoints.append(wpt)

with open('hidden_spots.gpx', 'w') as f:
    f.write(gpx.to_xml())
```

### Method 4: Mobile Apps

#### Organic Maps / OsmAnd
1. Convert CSV to GPX using script above
2. Copy GPX file to phone
3. Import in app: Menu → My Places → Import

#### Maps.me
1. Create KML from CSV
2. Share KML file to Maps.me app
3. Spots appear as bookmarks

#### Gaia GPS (Premium)
1. Upload GPX directly
2. Create custom map layers
3. Download for offline use

### Method 5: QGIS (Professional GIS)
```
1. Open QGIS
2. Layer → Add Layer → Add Delimited Text Layer
3. Select spots_coordinates.csv
4. Set X=longitude, Y=latitude
5. CRS: EPSG:4326 (WGS 84)
6. Style by attributes (type, is_hidden)
```

### Method 6: Web Integration
```html
<!-- Simple Leaflet.js map -->
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
</head>
<body>
    <div id="map" style="height: 600px;"></div>
    <script>
        var map = L.map('map').setView([43.6047, 1.4442], 9);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        
        // Load spots from JSON
        fetch('hidden_spots_export.json')
            .then(response => response.json())
            .then(spots => {
                spots.forEach(spot => {
                    if (spot.latitude && spot.longitude) {
                        var marker = L.marker([spot.latitude, spot.longitude])
                            .bindPopup(`<b>${spot.extracted_name}</b><br>
                                       Type: ${spot.location_type}<br>
                                       ${spot.is_hidden ? '🔐 Hidden' : '📍 Public'}`);
                        marker.addTo(map);
                    }
                });
            });
    </script>
</body>
</html>
```

## 🎨 Custom Markers by Category

### Water Spots (💧)
- Swimming holes
- Secret beaches
- Hidden waterfalls
- River access points

### Hot Springs (♨️)
- Natural thermal sources
- Wild hot springs
- Free thermal pools

### Urbex (🏚️)
- Abandoned buildings
- Industrial sites
- Historical ruins

### Caves (🕳️)
- Grottos
- Underground passages
- Natural caves

### Viewpoints (👁️)
- Secret overlooks
- Hidden vistas
- Sunrise/sunset spots

## 📱 Sharing Methods

### Private Sharing
1. **Encrypted GPX**: Use GPG to encrypt before sharing
2. **Private Google Map**: Share with specific emails only
3. **Password-protected KML**: ZIP with password

### Offline Use
1. Download map tiles for target area
2. Save GPX/KML to device
3. Use offline-capable apps (OsmAnd, Organic Maps)

## 🔐 Security Considerations

1. **Remove sensitive spots** before public sharing
2. **Generalize coordinates** for protected areas (+/- 0.001°)
3. **Add warnings** for dangerous locations
4. **Respect private property** markers

## 📊 Quick Statistics
- Total GPS coordinates: 67
- Hidden spots with GPS: ~20
- Within 50km of Toulouse: ~30
- Best documented: Le Fauga swimming spot

## 🚀 Next Steps

1. Run the visualizer:
   ```bash
   cd ~/projects/secret-toulouse-spots/scrapers
   python visualize_toulouse_spots.py
   firefox toulouse_spots_map.html
   ```

2. Import to phone:
   - Convert to GPX
   - Upload to Google My Maps
   - Share private link

3. Plan visits:
   - Start with closest spots
   - Group by type/area
   - Check seasonal access