"""
Critical Instagram Scraper Code for Analysis
Goal: Scrape Instagram for secret spots but handle the challenge of no official API
"""

class UnifiedInstagramScraper(BaseScraper):
    """Unified Instagram scraper with multiple operation modes"""
    
    # Hashtags for Toulouse secret spots
    HASHTAGS = [
        # French
        "toulousesecret", "spotsecrettoulouse", "toulousecache",
        "randonneetoulouse", "baignadesauvage", "cascadecachee",
        
        # Activities  
        "baignadesauvagetoulouse", "urbextoulouse", "randonneeoccitanie",
        "spotnaturetoulouse", "grotteoccitanie", "abandonedtoulouse",
        
        # Generic but localized
        "hautegaronnesecrete", "occitaniesecrete", "pyreneessecret",
        "sudouestsecret", "spotsecretfrance", "hiddenfrance"
    ]
    
    def __init__(self, mode: str = "basic", credentials: Optional[Dict] = None):
        """
        Initialize scraper with specified mode
        
        Args:
            mode: "basic" (no auth), "instagrapi" (with auth), or "selenium" 
            credentials: Dict with username/password for authenticated modes
        """
        super().__init__("instagram")
        self.mode = mode
        self.client = None
        self.driver = None
        
        # Setup for different modes
        if mode == "instagrapi":
            if not HAS_INSTAGRAPI:
                self.logger.error("instagrapi not installed")
                self.mode = "basic"
            elif credentials:
                self._setup_instagrapi_client(credentials)
            else:
                self.logger.warning("No credentials, falling back to basic")
                self.mode = "basic"
        elif mode == "selenium":
            self._setup_selenium_driver()
    
    def _scrape_selenium(self, hashtags: List[str], posts_per_tag: int) -> List[Dict]:
        """Scrape using Selenium (visual browser)"""
        self.logger.info("Running Selenium Instagram scraper")
        spots = []
        
        for hashtag in hashtags:
            try:
                # Navigate to hashtag page
                url = f"https://www.instagram.com/explore/tags/{hashtag}/"
                self.driver.get(url)
                time.sleep(random.uniform(3, 5))
                
                # Wait for posts to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article a"))
                )
                
                # Get post links
                posts = self.driver.find_elements(By.CSS_SELECTOR, "article a")[:posts_per_tag]
                post_urls = [post.get_attribute("href") for post in posts]
                
                # Extract from each post
                for post_url in post_urls:
                    try:
                        spot_data = self._extract_post_selenium(post_url)
                        if spot_data:
                            spots.append(spot_data)
                        time.sleep(random.uniform(2, 4))
                    except Exception as e:
                        self.logger.error(f"Error extracting post: {e}")
                        
            except Exception as e:
                self.logger.error(f"Error scraping #{hashtag}: {e}")
                
        return spots
    
    def _extract_post_selenium(self, post_url: str) -> Optional[Dict]:
        """Extract spot data from Instagram post using Selenium"""
        self.driver.get(post_url)
        time.sleep(2)
        
        try:
            # Get caption text
            caption_elem = self.driver.find_element(
                By.CSS_SELECTOR, 
                "h1 + span, article div span"
            )
            caption = caption_elem.text if caption_elem else ""
            
            # Extract location info
            location_elem = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/locations/']")
            location_name = location_elem[0].text if location_elem else None
            
            # Check if it's a secret spot
            if not self.is_secret_spot(caption):
                return None
                
            # Extract coordinates from caption
            coords = self.extract_coordinates(caption)
            
            # Get location type and activities
            location_type = self._guess_location_type(caption)
            activities = self._extract_activities(caption)
            
            return {
                "source": "instagram",
                "source_url": post_url,
                "raw_text": caption[:1000],
                "extracted_name": location_name or f"Instagram spot from {post_url.split('/')[-2]}",
                "latitude": coords[0] if coords else None,
                "longitude": coords[1] if coords else None,
                "location_type": location_type,
                "activities": activities,
                "is_hidden": 1,
                "metadata": {
                    "hashtags": self._extract_hashtags(caption),
                    "scraped_with": "selenium"
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing post {post_url}: {e}")
            return None