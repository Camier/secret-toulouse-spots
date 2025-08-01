#!/usr/bin/env python3
"""Scraper for small regional tourism websites in Occitanie"""

import re
import sqlite3
import time
from datetime import datetime
from typing import Dict, List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


class RegionalTourismScraper:
    """Scrape small regional tourism sites for hidden spots"""

    def __init__(self):
        self.db_path = "hidden_spots.db"

        # Toulouse coordinates
        self.toulouse_lat = 43.6047
        self.toulouse_lng = 1.4442

        # Regional tourism websites
        self.tourism_sites = [
            # Lot department
            {
                "name": "Lot Tourisme",
                "url": "https://www.tourisme-lot.com",
                "search_paths": [
                    "/explorer/baignades-et-activites-nautiques",
                    "/explorer/sites-naturels",
                    "/explorer/grottes-et-gouffres",
                ],
            },
            # Specific villages/areas
            {
                "name": "Vallée du Lot et du Célé",
                "url": "https://www.vallee-du-lot-et-du-cele.com",
                "search_paths": ["/decouvrir/sites-naturels", "/activites/baignade"],
            },
            # Tarn department
            {
                "name": "Tourisme Tarn",
                "url": "https://www.tourisme-tarn.com",
                "search_paths": [
                    "/decouvrir/sites-naturels/lacs-et-plans-deau",
                    "/decouvrir/sites-naturels/gorges-et-vallees",
                ],
            },
            # Ariège
            {
                "name": "Ariège Pyrénées",
                "url": "https://www.ariegepyrenees.com",
                "search_paths": [
                    "/decouvrir/grottes-et-gouffres",
                    "/activites-sportives/baignade",
                    "/randonnees",
                ],
            },
            # Aveyron
            {
                "name": "Tourisme Aveyron",
                "url": "https://www.tourisme-aveyron.com",
                "search_paths": [
                    "/voir-faire/nature/lacs-rivieres",
                    "/voir-faire/sites-remarquables",
                ],
            },
            # Small village sites
            {
                "name": "Saint-Cirq-Lapopie",
                "url": "https://www.saint-cirq-lapopie.com",
                "search_paths": ["/"],
            },
            # Gers
            {
                "name": "Tourisme Gers",
                "url": "https://www.tourisme-gers.com",
                "search_paths": ["/decouvrir/nature-et-paysages"],
            },
        ]

        # Keywords to look for
        self.hidden_keywords = [
            "secret",
            "caché",
            "méconnu",
            "peu connu",
            "sauvage",
            "préservé",
            "confidentiel",
            "hors des sentiers battus",
            "authentique",
            "insolite",
            "à l'écart",
        ]

        self.activity_keywords = [
            "baignade",
            "cascade",
            "lac",
            "source",
            "piscine naturelle",
            "grotte",
            "gouffre",
            "spéléologie",
            "exploration",
            "randonnée",
            "sentier",
            "chemin",
            "ruine",
            "château",
            "abandonné",
        ]

        # Setup Chrome options
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--window-size=1920,1080")
        self.chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        )

    def extract_locations_from_text(self, text: str) -> List[Dict]:
        """Extract location names and potential coordinates"""
        locations = []

        # Location name patterns
        location_patterns = [
            # Specific place names
            r"(?:cascade|lac|gouffre|grotte|source|gorges?|vallée|col|pic|mont) (?:de |du |des |d\')?([A-ZÀ-Ü][a-zà-ÿ\-\s]+)",
            # Village/town names
            r"(?:à |près de |proche de |aux alentours de )([A-ZÀ-Ü][a-zà-ÿ\-]+(?:-[A-ZÀ-Ü][a-zà-ÿ\-]+)*)",
            # GPS pattern
            r"(\d{1,2}[.,]\d+)[°\s]*[NS]?\s*[,/]\s*(\d{1,2}[.,]\d+)[°\s]*[EW]?",
        ]

        for pattern in location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):  # GPS coordinates
                    try:
                        lat = float(match[0].replace(",", "."))
                        lng = float(match[1].replace(",", "."))
                        if 41 < lat < 46 and -2 < lng < 5:  # France bounds
                            locations.append(
                                {"type": "coordinates", "lat": lat, "lng": lng}
                            )
                    except:
                        pass
                else:
                    # Clean up location name
                    name = match.strip()
                    if len(name) > 3:  # Filter out too short names
                        locations.append({"type": "name", "name": name})

        return locations

    def is_hidden_spot(self, text: str) -> bool:
        """Check if text indicates a hidden spot"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.hidden_keywords)

    def is_relevant_activity(self, text: str) -> bool:
        """Check if text mentions relevant outdoor activities"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.activity_keywords)

    def scrape_page(self, driver, url: str, site_name: str) -> List[Dict]:
        """Scrape a specific page for locations"""
        print(f"   📄 Scraping: {url}")
        locations_data = []

        try:
            driver.get(url)
            time.sleep(3)  # Wait for page load

            # Get all text content
            body = driver.find_element(By.TAG_NAME, "body")
            page_text = body.text

            # Look for location cards/articles
            selectors = [
                "article",
                ".card",
                ".location",
                ".site",
                ".lieu",
                ".destination",
                ".poi",
                '[class*="spot"]',
                '[class*="place"]',
            ]

            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)

                    for element in elements:
                        text = element.text

                        # Check if relevant
                        if self.is_relevant_activity(text) or self.is_hidden_spot(text):
                            # Extract locations
                            locations = self.extract_locations_from_text(text)

                            if locations:
                                # Get any links
                                links = element.find_elements(By.TAG_NAME, "a")
                                detail_url = (
                                    links[0].get_attribute("href") if links else url
                                )

                                location_data = {
                                    "site_name": site_name,
                                    "page_url": url,
                                    "detail_url": detail_url,
                                    "text": text[:500],
                                    "locations": locations,
                                    "is_hidden": self.is_hidden_spot(text),
                                }
                                locations_data.append(location_data)

                except Exception as e:
                    continue

            # Also check for specific patterns in full page text
            if not locations_data:
                # Split into paragraphs
                paragraphs = page_text.split("\n\n")

                for para in paragraphs:
                    if self.is_relevant_activity(para):
                        locations = self.extract_locations_from_text(para)
                        if locations:
                            location_data = {
                                "site_name": site_name,
                                "page_url": url,
                                "detail_url": url,
                                "text": para[:500],
                                "locations": locations,
                                "is_hidden": self.is_hidden_spot(para),
                            }
                            locations_data.append(location_data)

        except Exception as e:
            print(f"   ⚠️ Error scraping page: {e}")

        return locations_data

    def scrape_site(self, site_config: Dict) -> List[Dict]:
        """Scrape a tourism website"""
        print(f"\n🌐 Scraping {site_config['name']}...")
        all_locations = []

        driver = webdriver.Chrome(options=self.chrome_options)

        try:
            # Visit each search path
            for path in site_config["search_paths"]:
                url = site_config["url"] + path
                locations = self.scrape_page(driver, url, site_config["name"])
                all_locations.extend(locations)

                # Be polite
                time.sleep(2)

            print(f"   ✓ Found {len(all_locations)} potential locations")

        except Exception as e:
            print(f"   ❌ Error scraping site: {e}")
        finally:
            driver.quit()

        return all_locations

    def save_to_database(self, locations_data: List[Dict]):
        """Save scraped locations to database"""
        if not locations_data:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        saved = 0
        for data in locations_data:
            try:
                # Save each location mention
                for loc in data["locations"]:
                    location_name = loc.get("name", "Unknown")
                    lat = loc.get("lat")
                    lng = loc.get("lng")

                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO scraped_locations
                        (source, source_url, raw_text, extracted_name,
                         latitude, longitude, is_hidden, scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            f'tourism_{data["site_name"].lower().replace(" ", "_")}',
                            data["detail_url"],
                            data["text"],
                            location_name,
                            lat,
                            lng,
                            1 if data["is_hidden"] else 0,
                            datetime.now().isoformat(),
                        ),
                    )

                    if cursor.rowcount > 0:
                        saved += 1

            except Exception as e:
                print(f"   Error saving location: {e}")

        conn.commit()
        conn.close()

        print(f"   💾 Saved {saved} locations")

    def run_full_scrape(self):
        """Scrape all tourism sites"""
        print("🗺️ Starting regional tourism sites scraping...")
        print(f"   Target sites: {len(self.tourism_sites)}")

        all_locations = []

        for site in self.tourism_sites:
            locations = self.scrape_site(site)
            all_locations.extend(locations)
            self.save_to_database(locations)

        print(f"\n✅ Regional tourism scraping complete!")
        print(f"   Total locations found: {len(all_locations)}")

        # Summary by site
        sites_summary = {}
        for loc in all_locations:
            site = loc["site_name"]
            sites_summary[site] = sites_summary.get(site, 0) + len(loc["locations"])

        print("\n📊 Locations by site:")
        for site, count in sites_summary.items():
            print(f"   {site}: {count}")


if __name__ == "__main__":
    scraper = RegionalTourismScraper()
    scraper.run_full_scrape()
