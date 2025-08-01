# 🔄 Secret Spots Workflows

Automated workflows for discovering, verifying, and mapping secret spots around Toulouse.

## Available Workflows

### 1. 🔍 Full Discovery Pipeline
```bash
# Discovers new spots from all sources
./run_discovery.sh

# Or use the workflow:
/workflow spot-discovery
```

### 2. 🗺️ Map Update
```bash
# Updates web viewer with latest data
./workflows/map-update.sh

# Opens interactive map at http://localhost:8000
```

### 3. ✅ Spot Verification
```bash
# Checks for duplicates and data quality
python3 ./workflows/verify-spots.py

# Generates verification_report.json
```

### 4. 🚀 Quick Workflows

#### Add New Spot Manually
```bash
/workflow add-spot "Cascade Secrète" 44.123 3.567 "waterfall" "swimming,hiking"
```

#### Export for GPS Device
```bash
/workflow export-gpx
# Creates hidden_spots.gpx for Garmin/phone
```

#### Weekly Report
```bash
/workflow weekly-report
# Summarizes discoveries, updates stats
```

## Workflow Components

### Data Flow
```
Sources → Scrapers → Database → Verification → Export → Map
   ↑                                              ↓
   └──────────────── Feedback Loop ←─────────────┘
```

### File Structure
```
workflows/
├── README.md              # This file
├── spot-discovery.yaml    # Full discovery pipeline
├── map-update.sh         # Update web viewer
├── verify-spots.py       # Data verification
├── verification_report.json  # Latest verification
└── logs/                 # Workflow execution logs
```

## Custom Workflow Examples

### Morning Check
```bash
/workflow create "morning-spots" "
  bash 'cd ~/projects/secret-toulouse-spots' →
  verify-spots →
  map-update →
  notify 'Morning spot check complete'
"
```

### Instagram Discovery
```bash
/workflow create "insta-spots" "
  bash 'python scrapers/instagram_scraper_secure.py' →
  verify-spots →
  memory 'Instagram discovery session' →
  map-update
"
```

### Share Discoveries
```bash
/workflow create "share-spots" "
  export-gpx →
  export-csv →
  github create-gist spots_coordinates.csv →
  notify 'Spots shared successfully'
"
```

## Scheduled Workflows

Add to crontab for automation:
```bash
# Daily discovery at 2 AM
0 2 * * * cd ~/projects/secret-toulouse-spots && ./run_discovery.sh

# Weekly verification on Sundays
0 10 * * 0 cd ~/projects/secret-toulouse-spots && python3 workflows/verify-spots.py

# Monthly comprehensive report
0 9 1 * * cd ~/projects/secret-toulouse-spots && ./workflows/monthly-report.sh
```

## Integration with Claude

These workflows integrate with Claude's tools:
- **memory**: Stores discovery sessions
- **notify**: Desktop notifications
- **smart-tree**: Analyzes project structure
- **github**: Can share discoveries
- **obsidian**: Documents findings

## Tips

1. **Always verify** new spots before adding to map
2. **Backup database** before major discoveries
3. **Check duplicates** regularly (100m threshold)
4. **Respect privacy** - some spots are secret for a reason
5. **Test coordinates** - must be within 200km of Toulouse

## Troubleshooting

### Web server issues
```bash
pkill -f "http.server 8000"
cd ~/projects/secret-toulouse-spots
python3 -m http.server 8000
```

### Database locked
```bash
fuser hidden_spots.db  # Check who's using it
sqlite3 hidden_spots.db "VACUUM;"  # Clean up
```

### Missing dependencies
```bash
pip install requests folium sqlite3
```

---

*Happy discovering! 🗺️✨*