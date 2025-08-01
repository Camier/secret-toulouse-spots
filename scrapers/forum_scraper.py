#!/usr/bin/env python3
"""
Forum Scraper for Hidden French Outdoor Spots
Implements BeautifulSoup + Selenium for dynamic forum content extraction
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Dict, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup, SoupStrainer
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FrenchOutdoorForumScraper:
    """Scraper for French outdoor forums with focus on hidden spots"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.session_data = {
            "start_time": datetime.now(),
            "forums_scraped": [],
            "posts_extracted": 0,
            "locations_found": 0,
        }
    def __enter__(self):
        self.setup_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            self.driver.quit()


        # Target forums configuration
        self.forums = {
            "randonner.fr": {
                "base_url": "https://www.randonner.fr",
                "search_paths": ["/forum/", "/randonnees/", "/cascades-cachees/"],
                "post_selector": "div.post-content, div.message-body",
                "pagination": "a.pagination-next",
                "location_patterns": [
                    r"cascade(?:s)? (?:de |d\')?([A-Z][a-zÀ-ÿ\-\s]+)",
                    r"source(?:s)? (?:de |d\')?([A-Z][a-zÀ-ÿ\-\s]+)",
                    r"(?:près|proche) (?:de |d\')?([A-Z][a-zÀ-ÿ\-\s]+)",
                    r"baignade (?:sauvage |secrète )?(?:à |au |aux )?([A-Z][a-zÀ-ÿ\-\s]+)",
                ],
            },
            "camptocamp.org": {
                "base_url": "https://www.camptocamp.org",
                "search_paths": ["/forums/", "/routes/", "/waypoints/"],
                "post_selector": "div.comment-body, div.route-description",
                "pagination": "button.load-more",
                "location_patterns": [
                    r"(?:spot|endroit|lieu) (?:secret|caché|peu connu) (?:à |au |aux )?([A-Z][a-zÀ-ÿ\-\s]+)",
                    r"(?:lac|étang) (?:de |d\')?([A-Z][a-zÀ-ÿ\-\s]+)",
                    r"(?:grotte|caverne) (?:de |d\')?([A-Z][a-zÀ-ÿ\-\s]+)",
                ],
            },
            "nageurs.com": {
                "base_url": "https://www.nageurs.com",
                "search_paths": ["/forum/", "/spots-baignade/", "/eau-libre/"],
                "post_selector": "div.forum-post, div.spot-description",
                "pagination": "a.next-page",
                "location_patterns": [
                    r"(?:piscine|bassin) naturel(?:le)? (?:de |d\'|à )?([A-Z][a-zÀ-ÿ\-\s]+)",
                    r"(?:trou|vasque) (?:d\'eau |de baignade )?(?:à |au |aux )?([A-Z][a-zÀ-ÿ\-\s]+)",
                    r"baignade (?:interdite |non surveillée )(?:à |au |aux )?([A-Z][a-zÀ-ÿ\-\s]+)",
                ],
            },
        }

        # Keywords for finding hidden spots
        self.hidden_spot_keywords = [
            "secret",
            "caché",
            "peu connu",
            "hors des sentiers battus",
            "confidentiel",
            "locals only",
            "pas touristique",
            "préservé",
            "sauvage",
            "isolé",
            "tranquille",
            "méconnu",
            "discret",
        ]

        # Activity types
        self.activity_keywords = {
            "baignade": [
                "baignade",
                "nager",
                "piscine naturelle",
                "vasque",
                "trou d'eau",
            ],
            "cascade": ["cascade", "chute", "saut"],
            "randonnee": ["randonnée", "sentier", "chemin", "GR", "boucle"],
            "escalade": ["escalade", "grimpe", "voie", "falaise", "bloc"],
            "grotte": ["grotte", "caverne", "gouffre", "aven"],
            "source": ["source", "résurgence", "fontaine"],
            "bivouac": ["bivouac", "camping sauvage", "nuit", "dormir"],
        }

    def setup_driver(self):
        """Initialize Selenium WebDriver with optimized settings"""
        options = Options()
        if self.headless:
            options.add_argument("--headless")

        # Performance optimizations
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-images")  # Don't load images
        options.add_argument("--disable-javascript")  # For static content

        # French locale
        options.add_argument("--lang=fr-FR")

        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(30)

    def extract_locations_from_text(self, text: str, patterns: List[str]) -> List[Dict]:
        """Extract location mentions from text using regex patterns"""
        locations = []

        # Clean text
        text = re.sub(r"\s+", " ", text)

        # Check for hidden spot keywords
        is_hidden = any(
            keyword in text.lower() for keyword in self.hidden_spot_keywords
        )

        # Extract locations with patterns
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                location_name = match.group(1).strip()

                # Get context around the match
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end]

                # Detect activity type
                activity_type = "unknown"
                for activity, keywords in self.activity_keywords.items():
                    if any(kw in context.lower() for kw in keywords):
                        activity_type = activity
                        break

                locations.append(
                    {
                        "name": location_name,
                        "context": context,
                        "is_hidden": is_hidden,
                        "activity_type": activity_type,
                        "pattern_matched": pattern,
                    }
                )

        return locations

    def scrape_forum_page(self, url: str, forum_config: Dict) -> List[Dict]:
        """Scrape a single forum page for locations"""
        logger.info(f"Scraping: {url}")
        posts_data = []

        try:
            self.driver.get(url)

            # Wait for content to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, forum_config["post_selector"])
                )
            )

            # Parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, "lxml")

            # Use SoupStrainer for efficiency
            parse_only = SoupStrainer(
                name=["div", "article", "section"],
                class_=re.compile("post|message|comment|content"),
            )

            # Extract posts
            posts = soup.find_all(parse_only)

            for post in posts:
                post_text = post.get_text(strip=True, separator=" ")

                # Skip short posts
                if len(post_text) < 50:
                    continue

                # Extract metadata
                author = post.find(class_=re.compile("author|username|user"))
                date = post.find(class_=re.compile("date|timestamp|time"))

                # Extract locations
                locations = self.extract_locations_from_text(
                    post_text, forum_config["location_patterns"]
                )

                if locations:
                    posts_data.append(
                        {
                            "url": url,
                            "author": (
                                author.get_text(strip=True) if author else "Anonymous"
                            ),
                            "date": date.get_text(strip=True) if date else None,
                            "text": post_text[:500],  # First 500 chars
                            "locations": locations,
                            "scraped_at": datetime.now().isoformat(),
                        }
                    )

                    self.session_data["locations_found"] += len(locations)

            self.session_data["posts_extracted"] += len(posts_data)

        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")

        return posts_data

    def discover_forum_urls(
        self, forum_name: str, forum_config: Dict, max_pages: int = 10
    ) -> List[str]:
        """Discover relevant forum URLs to scrape"""
        urls = []
        base_url = forum_config["base_url"]

        # Keywords to search for
        search_terms = [
            "cascade cachée",
            "spot secret",
            "baignade sauvage",
            "lieu peu connu",
            "hors sentiers battus",
            "grotte secrète",
            "source thermale",
            "bivouac sauvage",
        ]

        for path in forum_config["search_paths"]:
            try:
                url = urljoin(base_url, path)
                self.driver.get(url)

                # Find all thread/topic links
                soup = BeautifulSoup(self.driver.page_source, "lxml")
                links = soup.find_all("a", href=True)

                for link in links:
                    href = link.get("href")
                    text = link.get_text(strip=True).lower()

                    # Check if link text contains our keywords
                    if any(term in text for term in search_terms):
                        full_url = urljoin(base_url, href)
                        if full_url not in urls and forum_name in full_url:
                            urls.append(full_url)

                            if len(urls) >= max_pages:
                                return urls

            except Exception as e:
                logger.error(f"Error discovering URLs for {forum_name}: {str(e)}")

        return urls[:max_pages]

    async def scrape_all_forums(self, max_pages_per_forum: int = 20) -> Dict:
        """Main method to scrape all configured forums"""
        all_data = {
            "metadata": {
                "scrape_date": datetime.now().isoformat(),
                "forums": list(self.forums.keys()),
                "total_locations": 0,
                "total_posts": 0,
            },
            "data": [],
        }

        self.setup_driver()

        try:
            for forum_name, forum_config in self.forums.items():
                logger.info(f"Starting scrape of {forum_name}")

                # Discover URLs
                urls = self.discover_forum_urls(
                    forum_name, forum_config, max_pages_per_forum
                )
                logger.info(f"Found {len(urls)} relevant pages to scrape")

                # Scrape each URL
                forum_data = []
                for url in urls:
                    posts = self.scrape_forum_page(url, forum_config)
                    forum_data.extend(posts)

                    # Be respectful - wait between requests
                    await asyncio.sleep(2)

                all_data["data"].extend(forum_data)
                self.session_data["forums_scraped"].append(forum_name)

        finally:
            if self.driver:
                self.driver.quit()

        # Update metadata
        all_data["metadata"]["total_locations"] = self.session_data["locations_found"]
        all_data["metadata"]["total_posts"] = self.session_data["posts_extracted"]
        all_data["metadata"]["session_data"] = self.session_data

        return all_data

    def save_results(self, data: Dict, output_file: str = "forum_hidden_spots.json"):
        """Save scraped data to JSON file"""
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(
            f"Saved {data['metadata']['total_locations']} locations to {output_file}"
        )


async def main():
    """Main execution function"""
    scraper = FrenchOutdoorForumScraper(headless=True)

    try:
        # Run the scraper
        results = await scraper.scrape_all_forums(max_pages_per_forum=10)

        # Save results
        scraper.save_results(results, "scraped_data/forum_hidden_spots.json")

        # Print summary
        print(f"\nScraping Complete!")
        print(f"Forums scraped: {len(results['metadata']['forums'])}")
        print(f"Total posts analyzed: {results['metadata']['total_posts']}")
        print(f"Hidden locations found: {results['metadata']['total_locations']}")

    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())