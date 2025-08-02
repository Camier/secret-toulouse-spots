#!/usr/bin/env python3
"""
Data validation using schema library with enhanced validation rules
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from schema import Schema, And, Or, Use, Optional as SchemaOptional, SchemaError

logger = logging.getLogger(__name__)


class SpotDataValidator:
    """Enhanced data validator for spot information"""
    
    # Toulouse region boundaries
    TOULOUSE_BOUNDS = {
        'lat_min': 42.5,
        'lat_max': 44.5,
        'lon_min': -1.0,
        'lon_max': 3.0
    }
    
    # Valid location types
    LOCATION_TYPES = [
        'natural', 'urban', 'abandoned', 'viewpoint', 'water',
        'ruins', 'park', 'trail', 'cave', 'building', 'bridge',
        'tunnel', 'forest', 'mountain', 'beach', 'lake', 'river',
        'waterfall', 'cascade'
    ]
    
    # Valid activities
    ACTIVITIES = [
        'hiking', 'climbing', 'swimming', 'photography', 'urbex',
        'camping', 'picnic', 'fishing', 'kayaking', 'cycling',
        'running', 'walking', 'exploring', 'stargazing', 'birdwatching'
    ]
    
    # Source-specific URL patterns
    URL_PATTERNS = {
        'reddit': re.compile(r'https?://(?:www\.)?reddit\.com/r/\w+/comments/\w+'),
        'instagram': re.compile(r'https?://(?:www\.)?instagram\.com/p/[\w-]+'),
        'osm': re.compile(r'https?://(?:www\.)?openstreetmap\.org/\w+/\d+'),
        'toulouse-blog': re.compile(r'https?://'),
        'routard': re.compile(r'https?://(?:www\.)?routard\.com/')
    }
    
    def __init__(self):
        """Initialize validator with schema definitions"""
        # Allow test source for testing
        self.allowed_sources = list(self.URL_PATTERNS.keys()) + ['test']
        
        self.spot_schema = Schema({
            # Required fields
            'source': And(str, lambda s: s in self.allowed_sources),
            'source_url': And(str, Use(self._validate_url)),
            'raw_text': And(str, lambda s: len(s.strip()) > 10),
            'scraped_at': Or(str, Use(self._validate_datetime)),
            
            # Coordinates (optional but validated if present)
            SchemaOptional('latitude'): And(
                Or(float, Use(float)),
                lambda x: self.TOULOUSE_BOUNDS['lat_min'] <= x <= self.TOULOUSE_BOUNDS['lat_max']
            ),
            SchemaOptional('longitude'): And(
                Or(float, Use(float)),
                lambda x: self.TOULOUSE_BOUNDS['lon_min'] <= x <= self.TOULOUSE_BOUNDS['lon_max']
            ),
            
            # Optional fields with validation
            SchemaOptional('extracted_name'): And(
                str,
                lambda s: 3 <= len(s) <= 200
            ),
            SchemaOptional('location_type'): And(
                str,
                lambda s: s in self.LOCATION_TYPES
            ),
            SchemaOptional('activities'): And(
                str,
                Use(self._validate_activities)
            ),
            SchemaOptional('is_hidden'): And(
                Use(int),
                lambda x: x in [0, 1]
            ),
            SchemaOptional('metadata'): dict,
            
            # Additional validation fields
            SchemaOptional('confidence_score'): And(
                Or(float, Use(float)),
                lambda x: 0 <= x <= 1
            ),
            SchemaOptional('image_urls'): [str],
            SchemaOptional('tags'): [str]
        })
        
        # Compiled regex patterns
        self.coord_pattern = re.compile(
            r'(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)'
        )
        self.name_cleanup_pattern = re.compile(
            r'[\x00-\x1f\x7f-\x9f]'  # Control characters
        )
        
    def validate(self, data: Dict) -> Dict:
        """
        Validate and clean spot data
        
        Args:
            data: Raw spot data dictionary
            
        Returns:
            Validated and cleaned data
            
        Raises:
            SchemaError: If validation fails
        """
        try:
            # Pre-process data
            cleaned_data = self._preprocess_data(data)
            
            # Validate against schema
            validated = self.spot_schema.validate(cleaned_data)
            
            # Post-process and enhance
            enhanced = self._postprocess_data(validated)
            
            # Calculate confidence score if not present
            if 'confidence_score' not in enhanced:
                enhanced['confidence_score'] = self._calculate_confidence(enhanced)
                
            return enhanced
            
        except SchemaError as e:
            logger.error(f"Validation failed: {e}")
            raise
            
    def _preprocess_data(self, data: Dict) -> Dict:
        """Pre-process data before validation"""
        cleaned = data.copy()
        
        # Ensure scraped_at is present
        if 'scraped_at' not in cleaned:
            cleaned['scraped_at'] = datetime.now().isoformat()
            
        # Clean text fields
        for field in ['raw_text', 'extracted_name']:
            if field in cleaned and cleaned[field]:
                cleaned[field] = self._clean_text(cleaned[field])
                
        # Normalize coordinates
        if 'latitude' in cleaned and 'longitude' in cleaned:
            try:
                cleaned['latitude'] = float(cleaned['latitude'])
                cleaned['longitude'] = float(cleaned['longitude'])
            except (ValueError, TypeError):
                logger.warning("Invalid coordinates, removing")
                cleaned.pop('latitude', None)
                cleaned.pop('longitude', None)
                
        return cleaned
        
    def _postprocess_data(self, data: Dict) -> Dict:
        """Post-process validated data"""
        enhanced = data.copy()
        
        # Extract coordinates from text if not present
        if not all(k in enhanced for k in ['latitude', 'longitude']):
            coords = self._extract_coordinates(enhanced.get('raw_text', ''))
            if coords:
                enhanced['latitude'], enhanced['longitude'] = coords
                
        # Infer location type if not present
        if 'location_type' not in enhanced:
            enhanced['location_type'] = self._infer_location_type(
                enhanced.get('raw_text', '')
            )
            
        # Extract tags from text
        if 'tags' not in enhanced:
            enhanced['tags'] = self._extract_tags(enhanced.get('raw_text', ''))
            
        return enhanced
        
    def _validate_url(self, url: str) -> str:
        """Validate URL format and source"""
        if not url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid URL scheme: {url}")
            
        # Clean URL
        url = url.strip()
        
        # Could add more URL validation here
        return url
        
    def _validate_datetime(self, dt: Any) -> str:
        """Validate and normalize datetime"""
        if isinstance(dt, str):
            # Try to parse ISO format
            try:
                datetime.fromisoformat(dt.replace('Z', '+00:00'))
                return dt
            except ValueError:
                pass
                
        # Convert to ISO format
        if isinstance(dt, datetime):
            return dt.isoformat()
            
        # Default to now
        return datetime.now().isoformat()
        
    def _validate_activities(self, activities: Any) -> str:
        """Validate and normalize activities"""
        if isinstance(activities, list):
            # Filter valid activities
            valid = [a for a in activities if a in self.ACTIVITIES]
            return ', '.join(valid)
            
        if isinstance(activities, str):
            # Split and validate
            parts = [a.strip() for a in activities.split(',')]
            valid = [a for a in parts if a in self.ACTIVITIES]
            return ', '.join(valid)
            
        return ''
        
    def _clean_text(self, text: str) -> str:
        """Clean text fields"""
        # Remove control characters
        text = self.name_cleanup_pattern.sub(' ', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text.strip()
        
    def _extract_coordinates(self, text: str) -> Optional[Tuple[float, float]]:
        """Extract coordinates from text"""
        matches = self.coord_pattern.findall(text)
        
        for match in matches:
            try:
                lat, lon = float(match[0]), float(match[1])
                
                # Validate bounds
                if (self.TOULOUSE_BOUNDS['lat_min'] <= lat <= self.TOULOUSE_BOUNDS['lat_max'] and
                    self.TOULOUSE_BOUNDS['lon_min'] <= lon <= self.TOULOUSE_BOUNDS['lon_max']):
                    return lat, lon
                    
            except ValueError:
                continue
                
        return None
        
    def _infer_location_type(self, text: str) -> str:
        """Infer location type from text"""
        text_lower = text.lower()
        
        # Check for keywords
        type_keywords = {
            'natural': ['nature', 'forest', 'bois', 'forêt', 'prairie'],
            'water': ['lac', 'lake', 'rivière', 'river', 'cascade', 'waterfall'],
            'abandoned': ['abandonné', 'abandoned', 'ruins', 'ruines'],
            'viewpoint': ['vue', 'view', 'panorama', 'belvédère'],
            'urban': ['ville', 'city', 'urbain', 'street', 'rue'],
            'trail': ['sentier', 'trail', 'chemin', 'path', 'randonnée']
        }
        
        for loc_type, keywords in type_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return loc_type
                
        return 'natural'  # Default
        
    def _extract_tags(self, text: str) -> List[str]:
        """Extract relevant tags from text"""
        tags = []
        text_lower = text.lower()
        
        # Secret/hidden indicators
        if any(word in text_lower for word in ['secret', 'caché', 'hidden', 'méconnu']):
            tags.append('secret')
            
        # Difficulty indicators
        if any(word in text_lower for word in ['difficile', 'difficult', 'climbing', 'escalade']):
            tags.append('challenging')
            
        # Time indicators
        if any(word in text_lower for word in ['sunset', 'coucher', 'sunrise', 'lever']):
            tags.append('golden-hour')
            
        return tags
        
    def _calculate_confidence(self, data: Dict) -> float:
        """Calculate confidence score for the spot data"""
        score = 0.0
        
        # Has coordinates: +0.4
        if all(k in data for k in ['latitude', 'longitude']):
            score += 0.4
            
        # Has name: +0.2
        if data.get('extracted_name'):
            score += 0.2
            
        # Has detailed description: +0.2
        if len(data.get('raw_text', '')) > 100:
            score += 0.2
            
        # Has activities: +0.1
        if data.get('activities'):
            score += 0.1
            
        # Has metadata/images: +0.1
        if data.get('metadata') or data.get('image_urls'):
            score += 0.1
            
        return min(score, 1.0)
        
    def validate_batch(self, spots: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Validate a batch of spots
        
        Returns:
            Tuple of (valid_spots, invalid_spots)
        """
        valid = []
        invalid = []
        
        for spot in spots:
            try:
                validated = self.validate(spot)
                valid.append(validated)
            except SchemaError as e:
                logger.warning(f"Validation failed for spot: {e}")
                invalid.append({
                    'data': spot,
                    'error': str(e)
                })
                
        logger.info(f"Batch validation: {len(valid)} valid, {len(invalid)} invalid")
        return valid, invalid


# Example usage
if __name__ == "__main__":
    validator = SpotDataValidator()
    
    # Test data
    test_spot = {
        'source': 'reddit',
        'source_url': 'https://reddit.com/r/toulouse/comments/abc123',
        'raw_text': 'Secret spot near Toulouse with amazing views. Coordinates: 43.604652, 1.444209',
        'extracted_name': 'Hidden Viewpoint',
        'activities': 'hiking, photography'
    }
    
    try:
        validated = validator.validate(test_spot)
        print("Validated successfully!")
        print(f"Confidence score: {validated['confidence_score']}")
        print(f"Extracted coords: {validated.get('latitude')}, {validated.get('longitude')}")
        print(f"Location type: {validated.get('location_type')}")
        print(f"Tags: {validated.get('tags')}")
    except SchemaError as e:
        print(f"Validation failed: {e}")