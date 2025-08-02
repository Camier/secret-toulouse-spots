"""
Comprehensive Scraper Code for Optimization Analysis
Including all unified scrapers and base class
"""

# BASE SCRAPER CLASS
class BaseScraper(ABC):
    """Base class for all scrapers with common functionality"""
    
    def __init__(self, source_name: str, db_path: str = "../hidden_spots.db"):
        self.source_name = source_name
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.rate_limit_delay = (1, 3)  # Min/max seconds between requests
        
        # Setup requests session with retry logic
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SecretSpotsScraper/1.0 (Educational Research)'
        })
        
        # Add retry logic
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Initialize enhanced modules if available
        if HAS_ENHANCED_MODULES:
            self.coord_extractor = EnhancedCoordinateExtractor()
            self.validator = SpotDataValidator()
    
    def rate_limit(self):
        """Apply rate limiting between requests"""
        delay = random.uniform(*self.rate_limit_delay)
        time.sleep(delay)
    
    def save_spot(self, spot_data: Dict) -> bool:
        """Save a single spot to database with validation"""
        try:
            # Validate data if validator available
            if self.validator:
                spot_data = self.validator.validate(spot_data)
            
            cursor.execute("""
                INSERT INTO spots (
                    source, source_url, raw_text, extracted_name,
                    latitude, longitude, location_type, activities,
                    is_hidden, scraped_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (...))
            
            conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Error saving spot: {e}")
            return False


# REDDIT SCRAPER
class UnifiedRedditScraper(BaseScraper):
    """Unified Reddit scraper with multiple operation modes"""
    
    SUBREDDITS = [
        "toulouse", "ToulouseCity", "HauteGaronne", "Occitanie",
        "france", "randonnee", "campingsauvage", "urbexfrance"
    ]
    
    def __init__(self, mode: str = "basic"):
        super().__init__("reddit")
        self.mode = mode
        self.reddit = None
        self.nlp_extractor = FrenchLocationExtractor()
        
        if mode == "praw" and HAS_PRAW:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                check_for_async=False
            )
            self.reddit.user.me()  # Verify auth
    
    def _scrape_praw(self, subreddits: List[str], limit: int) -> List[Dict]:
        """Scrape using PRAW (authenticated)"""
        spots = []
        
        for subreddit_name in subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                subreddit.id  # Validate exists
                
                for submission in subreddit.new(limit=limit):
                    if self._is_outdoor_post(submission):
                        extracted_spots = self._extract_spots_from_submission(submission)
                        spots.extend(extracted_spots)
                    self.rate_limit()
                    
            except Exception as e:
                self.logger.error(f"Error: {e}")
        
        return spots


# INSTAGRAM SCRAPER  
class UnifiedInstagramScraper(BaseScraper):
    """Unified Instagram scraper with multiple operation modes"""
    
    HASHTAGS = [
        "toulousesecret", "spotsecrettoulouse", "cascadecachee",
        "baignadesauvagetoulouse", "urbextoulouse", "grotteoccitanie"
    ]
    
    def _scrape_selenium(self, hashtags: List[str], posts_per_tag: int) -> List[Dict]:
        """Scrape using Selenium (visual browser)"""
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
                
                # Extract posts
                posts = self.driver.find_elements(By.CSS_SELECTOR, "article a")[:posts_per_tag]
                for post in posts:
                    spot_data = self._extract_post_selenium(post.get_attribute("href"))
                    if spot_data:
                        spots.append(spot_data)
                    time.sleep(random.uniform(2, 4))
                    
            except Exception as e:
                self.logger.error(f"Error: {e}")
        
        return spots


# DATA STANDARDIZATION EXAMPLE
def standardize_spot_data(raw_spot: Dict, source: str) -> Dict:
    """Current basic standardization approach"""
    return {
        "source": source,
        "source_url": raw_spot.get("url", ""),
        "raw_text": raw_spot.get("text", "")[:1000],
        "extracted_name": raw_spot.get("name", "Unknown"),
        "latitude": raw_spot.get("lat"),
        "longitude": raw_spot.get("lon"),
        "location_type": guess_location_type(raw_spot.get("text", "")),
        "activities": extract_activities(raw_spot.get("text", "")),
        "is_hidden": 1 if is_secret_spot(raw_spot.get("text", "")) else 0,
        "metadata": {
            "original_data": raw_spot
        }
    }