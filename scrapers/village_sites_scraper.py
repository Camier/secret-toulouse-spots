#!/usr/bin/env python3
"""Scraper for small village and local association websites"""

import re
import sqlite3
import time
from datetime import datetime
from typing import Dict, List

import requests
from bs4 import BeautifulSoup


class VillageSitesScraper:
    """Scrape small village websites and local tourism pages"""

    def __init__(self):
        self.db_path = "hidden_spots.db"

        # Small village and local sites
        self.village_sites = [
            # Lot villages
            {
                "name": "Liauzou",
                "urls": ["https://www.mairie-liauzou.fr/", "https://liauzou.fr/"],
                "keywords": ["cascade", "moulin", "source", "chemin"],
            },
            {
                "name": "Cabrerets",
                "urls": [
                    "https://www.cabrerets.fr/",
                    "https://www.pechmerle.com/",  # Grotte de Pech Merle
                ],
                "keywords": ["grotte", "rivière", "célé"],
            },
            {
                "name": "Marcilhac-sur-Célé",
                "urls": ["https://www.marcilhac-sur-cele.fr/"],
                "keywords": ["abbaye", "grotte", "source", "baignade"],
            },
            # Tarn villages
            {
                "name": "Ambialet",
                "urls": ["https://www.ambialet.fr/"],
                "keywords": ["méandre", "tarn", "prieuré"],
            },
            {
                "name": "Cordes-sur-Ciel",
                "urls": ["https://www.cordessurciel.fr/"],
                "keywords": ["puits", "jardin", "vue"],
            },
            # Ariège villages
            {
                "name": "Mirepoix",
                "urls": ["https://www.mirepoix.fr/"],
                "keywords": ["lac", "montbel", "forêt"],
            },
            # Local associations and blogs
            {
                "name": "Rando Occitanie Blog",
                "urls": [
                    "https://www.randonnee-occitanie.com/",
                    "https://www.visorando.com/randonnee-occitanie.html",
                ],
                "keywords": ["sentier", "gr", "refuge", "source"],
            },
            {
                "name": "Grottes et Gouffres Lot",
                "urls": [
                    "https://www.grottes-en-france.com/regions/occitanie/lot.html"
                ],
                "keywords": ["spéléologie", "gouffre", "exploration"],
            },
            # Nature and outdoor blogs
            {
                "name": "Baignades Sauvages France",
                "urls": ["https://www.les-baignades-sauvages.com/region/occitanie/"],
                "keywords": ["baignade", "cascade", "vasque", "piscine naturelle"],
            },
            # Micro-local sites
            {
                "name": "Villages du Quercy",
                "urls": ["https://www.quercy.net/villages/"],
                "keywords": ["pigeonnier", "lavoir", "moulin", "source"],
            },
        ]

        # Headers to appear as regular browser
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        }

        # Location extraction patterns
        self.location_patterns = {
            "specific_places": re.compile(
                r"(?:cascade|lac|gouffre|grotte|source|moulin|lavoir|dolmen|château|ruine|pont) "
                r"(?:de |du |des |d\')?([A-ZÀ-Ü][a-zà-ÿ\-\s]+)",
                re.IGNORECASE,
            ),
            "near_locations": re.compile(
                r"(?:près de|proche de|à côté de|aux alentours de|sur la commune de) "
                r"([A-ZÀ-Ü][a-zà-ÿ\-]+(?:-[A-ZÀ-Ü][a-zà-ÿ\-]+)*)",
                re.IGNORECASE,
            ),
            "directions": re.compile(
                r"(?:depuis|à partir de|en direction de|vers) "
                r"([A-ZÀ-Ü][a-zà-ÿ\-]+)[\s,]+"
                r"(?:prendre|suivre|continuer)",
                re.IGNORECASE,
            ),
            "distance": re.compile(
                r"à (\d+(?:,\d+)?)\s*(?:km|kilomètres?|m|mètres?) "
                r"(?:de |du |d\')([A-ZÀ-Ü][a-zà-ÿ\-]+)",
                re.IGNORECASE,
            ),
        }

    def extract_locations(self, text: str) -> List[Dict]:
        """Extract location mentions from text"""
        locations = []

        for pattern_name, pattern in self.location_patterns.items():
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    # Distance pattern returns (distance, place)
                    locations.append(
                        {
                            "name": match[1].strip(),
                            "distance": match[0],
                            "type": "relative",
                        }
                    )
                else:
                    name = match.strip()
                    if len(name) > 3:  # Filter short names
                        locations.append({"name": name, "type": pattern_name})

        return locations

    def is_outdoor_content(self, text: str) -> bool:
        """Check if content is about outdoor activities"""
        outdoor_keywords = [
            "randonnée",
            "balade",
            "promenade",
            "sentier",
            "chemin",
            "baignade",
            "cascade",
            "source",
            "rivière",
            "ruisseau",
            "grotte",
            "gouffre",
            "spéléologie",
            "exploration",
            "nature",
            "paysage",
            "panorama",
            "point de vue",
            "pique-nique",
            "aire",
            "refuge",
        ]

        text_lower = text.lower()
        return any(keyword in text_lower for keyword in outdoor_keywords)

    def scrape_url(self, url: str, site_name: str, keywords: List[str]) -> List[Dict]:
        """Scrape a specific URL"""
        print(f"   📄 Checking: {url}")
        locations_data = []

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "lxml")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text content
            text = soup.get_text()

            # Look for content sections
            content_sections = []

            # Try different content selectors
            selectors = [
                "article",
                "main",
                ".content",
                "#content",
                ".post",
                ".entry",
                ".text",
                "section",
            ]

            for selector in selectors:
                elements = soup.select(selector)
                for element in elements:
                    section_text = element.get_text()
                    if self.is_outdoor_content(section_text):
                        content_sections.append(section_text)

            # If no sections found, use paragraphs
            if not content_sections:
                paragraphs = soup.find_all("p")
                for p in paragraphs:
                    p_text = p.get_text()
                    if any(kw in p_text.lower() for kw in keywords):
                        content_sections.append(p_text)

            # Extract locations from content
            for section in content_sections:
                locations = self.extract_locations(section)

                if locations:
                    # Check if it mentions hidden/secret spots
                    is_hidden = any(
                        word in section.lower()
                        for word in [
                            "secret",
                            "caché",
                            "méconnu",
                            "peu connu",
                            "confidentiel",
                            "préservé",
                            "sauvage",
                        ]
                    )

                    location_data = {
                        "site_name": site_name,
                        "url": url,
                        "text": section[:500],
                        "locations": locations,
                        "is_hidden": is_hidden,
                    }
                    locations_data.append(location_data)

            # Also check for specific mentions in links
            links = soup.find_all("a", string=re.compile("|".join(keywords), re.I))
            for link in links:
                parent_text = link.parent.get_text() if link.parent else ""
                locations = self.extract_locations(parent_text)

                if locations:
                    location_data = {
                        "site_name": site_name,
                        "url": url,
                        "text": parent_text[:500],
                        "locations": locations,
                        "is_hidden": False,
                    }
                    locations_data.append(location_data)

        except Exception as e:
            print(f"   ⚠️ Error scraping {url}: {e}")

        return locations_data

    def scrape_village_site(self, site_config: Dict) -> List[Dict]:
        """Scrape a village website"""
        print(f"\n🏘️ Scraping {site_config['name']}...")
        all_locations = []

        for url in site_config["urls"]:
            locations = self.scrape_url(
                url, site_config["name"], site_config["keywords"]
            )
            all_locations.extend(locations)
            time.sleep(1)  # Be polite

        print(f"   ✓ Found {len(all_locations)} location mentions")
        return all_locations

    def save_to_database(self, locations_data: List[Dict]):
        """Save to database"""
        if not locations_data:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        saved = 0
        for data in locations_data:
            try:
                for loc in data["locations"]:
                    location_name = loc.get("name", "Unknown")

                    # Add context if it's a relative location
                    if loc.get("type") == "relative" and loc.get("distance"):
                        location_name = (
                            f"{location_name} ({loc['distance']} from reference)"
                        )

                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO scraped_locations
                        (source, source_url, raw_text, extracted_name,
                         latitude, longitude, is_hidden, scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            f'village_{data["site_name"].lower().replace(" ", "_")}',
                            data["url"],
                            data["text"],
                            location_name,
                            None,  # No GPS from these sites usually
                            None,
                            1 if data["is_hidden"] else 0,
                            datetime.now().isoformat(),
                        ),
                    )

                    if cursor.rowcount > 0:
                        saved += 1

            except Exception as e:
                print(f"   Error saving: {e}")

        conn.commit()
        conn.close()

        print(f"   💾 Saved {saved} locations")

    def run_full_scrape(self):
        """Scrape all village sites"""
        print("🏘️ Starting village sites scraping...")
        print(f"   Target sites: {len(self.village_sites)}")

        all_locations = []

        for site in self.village_sites:
            locations = self.scrape_village_site(site)
            all_locations.extend(locations)
            self.save_to_database(locations)

        print(f"\n✅ Village sites scraping complete!")
        print(
            f"   Total location mentions: {sum(len(loc['locations']) for loc in all_locations)}"
        )

        # Summary
        print("\n📊 Summary by village:")
        village_counts = {}
        for loc in all_locations:
            name = loc["site_name"]
            village_counts[name] = village_counts.get(name, 0) + len(loc["locations"])

        for village, count in village_counts.items():
            print(f"   {village}: {count} locations")


if __name__ == "__main__":
    scraper = VillageSitesScraper()
    scraper.run_full_scrape()