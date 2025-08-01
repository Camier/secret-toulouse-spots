"""
Critical Code Sections for Secret Toulouse Spots Project
Goal: Find and map secret/hidden outdoor spots around Toulouse using multiple data sources
"""

# SECTION 1: OSM Relevance Scoring Algorithm
# This is the core algorithm that filters 3,181 OSM spots down to ~1,800 relevant ones
def calculate_relevance_score(spot):
    """
    Calculate relevance score for an OSM spot based on multiple criteria.
    Higher score = more relevant/interesting
    """
    score = 0
    metadata = json.loads(spot["metadata"]) if spot["metadata"] else {}
    osm_tags = metadata.get("osm_tags", {})

    # 1. Named vs unnamed (+3 for proper names, -2 for generic names)
    name = spot["extracted_name"] or ""
    if name and not any(
        generic in name.lower() for generic in ["non nommée", "unnamed", "sans nom"]
    ):
        score += 3
    elif "non nommée" in name.lower():
        score -= 2

    # 2. Distance from Toulouse
    distance = metadata.get("distance_from_toulouse_km")
    if distance:
        if distance <= 20:
            score += 3  # Day trip distance
        elif distance <= 50:
            score += 2  # Easy weekend trip
        elif distance <= 100:
            score += 1  # Weekend trip
        else:
            score -= 1  # Far

    # 3. Accessibility (REVISED: difficult access = more secret/rare!)
    access = osm_tags.get("access", "")
    if access in ["private", "no"]:
        score += 2  # Private/restricted = more secret!
    elif access == "permissive":
        score += 1  # Semi-private = interesting
    elif access in ["yes", "public"]:
        score -= 1  # Too easy/public = less interesting

    # 10. Rarity indicators
    rarity_keywords = [
        "abandoned", "disused", "ruins", "hidden", "secret",
        "cache", "grotte", "souterrain"
    ]
    description_text = (
        osm_tags.get("description", "") + " " + osm_tags.get("name", "")
    ).lower()
    for keyword in rarity_keywords:
        if keyword in description_text:
            score += 2

    return score


# SECTION 2: Map Data Processing for Visualization
# This processes spots for the enhanced-map.html visualization
def process_spots_for_map():
    """Process spots from database and prepare data for map visualization"""
    print("💾 Processing spots for map visualization...")
    
    # Get all spots with coordinates
    cursor.execute("""
        SELECT id, source, extracted_name, latitude, longitude, 
               location_type, activities, is_hidden, raw_text, metadata
        FROM spots
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """)
    
    spots = cursor.fetchall()
    print(f"   Found {len(spots)} spots with coordinates")
    
    # Convert to JSON for map
    spots_data = []
    for spot in spots:
        # Skip if coordinates are invalid
        if not (-90 <= spot[3] <= 90) or not (-180 <= spot[4] <= 180):
            continue
            
        metadata = json.loads(spot[9]) if spot[9] else {}
        
        # Create spot object
        spot_obj = {
            "id": spot[0],
            "name": spot[2] or f"Spot from {spot[1]}",
            "lat": spot[3],
            "lng": spot[4],
            "source": spot[1],
            "location_type": spot[5] or "unknown",
            "activities": spot[6] or "",
            "is_hidden": spot[7],
            "description": spot[8][:200] if spot[8] else "",
            "metadata": metadata
        }
        
        spots_data.append(spot_obj)


# SECTION 3: Unified Scraper Architecture with Enhanced Modules
# This is the base class that all scrapers inherit from
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
        else:
            self.coord_extractor = None
            self.validator = None
    
    def save_spot(self, spot_data: Dict) -> bool:
        """Save a single spot to database with validation"""
        try:
            # Validate data if validator available
            if self.validator:
                try:
                    spot_data = self.validator.validate(spot_data)
                except Exception as e:
                    self.logger.error(f"Validation failed: {e}")
                    return False
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO spots (
                    source, source_url, raw_text, extracted_name,
                    latitude, longitude, location_type, activities,
                    is_hidden, scraped_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (...))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"Error saving spot: {e}")
            return False