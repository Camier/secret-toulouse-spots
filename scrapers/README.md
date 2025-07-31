# 🕷️ Scrapers Collection

Complete collection of scrapers used to discover hidden spots near Toulouse.

## 📋 Scraper Inventory

### Core Scrapers
- `main_scraper.py` - Main orchestrator that runs all scrapers
- `reddit_scraper.py` - Original Reddit scraper
- `reddit_mcp_scraper.py` - Enhanced Reddit scraper using MCP integration
- `regional_tourism_scraper.py` - Scrapes regional tourism websites
- `village_sites_scraper.py` - Extracts data from village websites
- `forum_scraper.py` - Scrapes outdoor forums (randonner-malin.com)
- `instagram_scraper_secure.py` - Secure Instagram location scraper

### Utilities
- `setup_database.py` - Creates SQLite database schema
- `nlp_location_extractor.py` - NLP-based location extraction
- `generate_comprehensive_report.py` - Generates final report
- `visualize_toulouse_spots.py` - Creates HTML map visualization
- `config.py` / `config_template.py` - Configuration management

## 🚀 Usage

### Initial Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Setup database
python setup_database.py

# Configure credentials (if needed)
cp config_template.py config.py
# Edit config.py with your credentials
```

### Running Scrapers

#### Run all scrapers:
```bash
python main_scraper.py
```

#### Run individual scrapers:
```bash
# Reddit with MCP
python reddit_mcp_scraper.py

# Regional tourism sites
python regional_tourism_scraper.py

# Village websites
python village_sites_scraper.py

# Forums
python forum_scraper.py
```

### Generate Report
```bash
python generate_comprehensive_report.py
```

### Create Map
```bash
python visualize_toulouse_spots.py
# Opens map in browser
```

## 🔐 Required Credentials

- **Reddit**: Set up in pass store
  - `pass insert reddit/client-id`
  - `pass insert reddit/client-secret`
- **Instagram**: Optional, uses config.json
- **Forums**: No authentication needed
- **Tourism sites**: No authentication needed

## 📊 Data Flow

1. Scrapers → `hidden_spots.db` (SQLite)
2. Database → `generate_comprehensive_report.py`
3. Report → `hidden_spots_export.json` + `spots_coordinates.csv`
4. Coordinates → `visualize_toulouse_spots.py` → HTML map

## 🎯 Scraping Targets

- **Reddit**: r/toulouse, r/france, r/randonnee, etc.
- **Tourism**: tourisme-occitanie.com, various CDT sites
- **Villages**: Cordes-sur-Ciel, Cabrerets, Quercy villages
- **Forums**: randonner-malin.com outdoor community
- **Instagram**: Location tags near Toulouse

## ⚠️ Ethical Scraping

- Respects robots.txt
- Includes delays between requests
- User-agent properly identified
- No excessive load on servers