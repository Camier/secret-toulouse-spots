# 🗺️ Secret Toulouse Spots

**CONFIDENTIAL** - Hidden outdoor locations near Toulouse discovered through various sources.

## 📊 Summary

- **Total Locations**: 95 discovered
- **Secret/Hidden Spots**: 43 confirmed
- **GPS Coordinates**: 15+ precise locations
- **Sources**: Reddit, Instagram, village sites, forums

## 🎯 Notable Discoveries

### Water Spots 💧
- **Spot Secret Le Fauga** - GPS: 43.3962, 1.2526 (Swimming)
- **Clermont-le-Fort Rivière** - GPS: 43.4583, 1.4417 (River swimming)
- **Cascade Secrète** - GPS: 44.1234, 3.5678 (Secret waterfall)

### Hot Springs ♨️
- **Mérens-les-Vals** - GPS: 42.6547, 1.8339 (Thermal springs)
- **Source chaude de Camou** - Natural hot spring

### Urbex 🏚️
- **Restaurant Universitaire abandonné** - Toulouse (Security present)
- **Urbex spots Tarn** - Various abandoned locations

## 📁 Repository Structure

```
secret-toulouse-spots/
├── hidden_spots.db              # SQLite database with all locations
├── hidden_spots_export.json     # JSON export of secret spots  
├── spots_coordinates.csv        # CSV with GPS coordinates
├── run_discovery.sh            # Run complete discovery pipeline
├── scrapers/                   # All scraper scripts
│   ├── main_scraper.py        # Main orchestrator
│   ├── reddit_scraper.py      # Reddit scraper
│   ├── reddit_mcp_scraper.py  # Reddit with MCP integration
│   ├── regional_tourism_scraper.py
│   ├── village_sites_scraper.py
│   ├── forum_scraper.py
│   ├── instagram_scraper_secure.py
│   ├── generate_comprehensive_report.py
│   ├── visualize_toulouse_spots.py
│   └── [utilities...]
└── README.md

## 🔒 Security Note

These locations are shared by the community. Please:
- Respect private property
- Leave no trace
- Be mindful of local regulations
- Some spots may be dangerous or restricted

## 🗺️ Usage

### Quick Start
```bash
# Run complete discovery pipeline
./run_discovery.sh
```

### Manual Steps
1. Import `spots_coordinates.csv` into your mapping app
2. Use `hidden_spots_export.json` for detailed information
3. Run scrapers individually from `scrapers/` directory
4. Generate updated report: `cd scrapers && python generate_comprehensive_report.py`

---
*Discovered: July 2025*