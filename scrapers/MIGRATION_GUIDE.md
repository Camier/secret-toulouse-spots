# Scraper Migration Guide

## Overview

The scraper architecture has been refactored to eliminate code duplication and provide a unified interface for all data sources.

## What Changed

### Removed Files
- `instagram_scraper.py` → Use `unified_instagram_scraper.py`
- `instagram_scraper_secure.py` → Use `unified_instagram_scraper.py` with `mode="secure"`
- `instagram_continuous_scraper.py` → Use `unified_instagram_scraper.py` with `mode="continuous"`
- `reddit_scraper.py` → Use `unified_reddit_scraper.py`
- `reddit_enhanced_scraper.py` → Use `unified_reddit_scraper.py`

### New Files
- `base_scraper.py` - Base class with common functionality
- `unified_instagram_scraper.py` - All Instagram scraping modes
- `unified_reddit_scraper.py` - All Reddit scraping modes
- `main_scraper_unified.py` - New orchestrator for all scrapers

## Migration Examples

### Instagram Scraping

**Old way:**
```python
# Basic scraping
from instagram_scraper import scrape_instagram
scrape_instagram()

# Secure scraping
from instagram_scraper_secure import SecureInstagramScraper
scraper = SecureInstagramScraper()
scraper.scrape()

# Continuous scraping
from instagram_continuous_scraper import run_continuous_scraper
run_continuous_scraper(duration=7200)
```

**New way:**
```python
from unified_instagram_scraper import UnifiedInstagramScraper

# Basic mode (simulated data)
scraper = UnifiedInstagramScraper(mode="basic")
scraper.run(limit=50)

# Secure mode (with authentication)
scraper = UnifiedInstagramScraper(
    mode="secure",
    username="your_username",
    password="your_password"
)
scraper.run(limit=100)

# Continuous mode (long-running simulation)
scraper = UnifiedInstagramScraper(
    mode="continuous",
    continuous_duration=7200  # 2 hours
)
scraper.run()
```

### Reddit Scraping

**Old way:**
```python
# Basic Reddit scraper
from reddit_scraper import RedditOutdoorScraper
scraper = RedditOutdoorScraper()
scraper.run_full_scrape()

# Enhanced Reddit scraper
from reddit_enhanced_scraper import main
main()
```

**New way:**
```python
from unified_reddit_scraper import UnifiedRedditScraper

# Basic mode
scraper = UnifiedRedditScraper(mode="basic")
scraper.run(limit=100)

# PRAW mode (authenticated)
scraper = UnifiedRedditScraper(
    mode="praw",
    client_id="your_client_id",
    client_secret="your_client_secret"
)
scraper.run(limit=200, subreddits=["toulouse", "randonnee"])
```

### Running All Scrapers

**Old way:**
```python
from main_scraper import HiddenSpotsAggregator
aggregator = HiddenSpotsAggregator()
aggregator.run_all_scrapers()
```

**New way:**
```bash
# Command line
python main_scraper_unified.py --sources all --limit 100

# With specific sources
python main_scraper_unified.py --sources instagram reddit osm

# With authentication
python main_scraper_unified.py \
    --instagram-mode secure \
    --instagram-username YOUR_USERNAME \
    --instagram-password YOUR_PASSWORD \
    --reddit-mode praw \
    --reddit-client-id YOUR_CLIENT_ID \
    --reddit-client-secret YOUR_SECRET
```

## Benefits of the New Architecture

1. **No Code Duplication**: Common functionality in base class
2. **Unified Interface**: Same methods across all scrapers
3. **Better Error Handling**: Centralized logging and error recovery
4. **Flexible Modes**: Easy to switch between basic/authenticated/continuous modes
5. **Easier Testing**: Mock base class for unit tests
6. **Better Configuration**: Command-line arguments for all options

## Backwards Compatibility

If you have scripts that depend on the old scrapers, you can create compatibility wrappers:

```python
# instagram_scraper.py (compatibility wrapper)
from unified_instagram_scraper import UnifiedInstagramScraper

def scrape_instagram():
    scraper = UnifiedInstagramScraper(mode="basic")
    return scraper.run()

# For class-based usage
class FrenchOutdoorInstagramScraper:
    def __init__(self):
        self.scraper = UnifiedInstagramScraper(mode="basic")
    
    def scrape(self):
        return self.scraper.run()
```

## Environment Variables

The new scrapers support environment variables for credentials:

```bash
# Instagram
export INSTAGRAM_USERNAME="your_username"
export INSTAGRAM_PASSWORD="your_password"

# Reddit
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"
```

## Next Steps

1. Update your scripts to use the new unified scrapers
2. Test with small limits first
3. Remove references to old scraper files
4. Use `main_scraper_unified.py` for orchestrated scraping