#!/usr/bin/env python3
"""
Data validation for spot data using schema library
Based on Ollama's suggestion for input validation
"""

from schema import Schema, And, Or, Optional, Use
from datetime import datetime
import re


class SpotDataValidator:
    """Validates spot data before database insertion"""
    
    # Valid location types
    LOCATION_TYPES = [
        'waterfall', 'cave', 'ruins', 'natural_pool', 'viewpoint',
        'abandoned_building', 'nature', 'water', 'mountain', 'forest',
        'historical', 'geological', 'unknown'
    ]
    
    # Valid activity types
    ACTIVITIES = [
        'baignade', 'randonnée', 'escalade', 'spéléologie', 'photo',
        'camping', 'pêche', 'vtt', 'kayak', 'observation', 'urbex',
        'cliff jumping', 'exploration'
    ]
    
    def __init__(self):
        """Initialize validation schema"""
        self.schema = Schema({
            # Required fields
            'source': And(str, len, lambda s: s.strip() != ''),
            'source_url': And(str, self._validate_url),
            'raw_text': And(str, len),
            'extracted_name': And(str, len, lambda s: len(s) < 200),
            
            # Optional coordinate fields with validation
            Optional('latitude'): Or(None, And(Use(float), 
                lambda n: 42.5 <= n <= 44.5)),
            Optional('longitude'): Or(None, And(Use(float), 
                lambda n: -1.0 <= n <= 3.0)),
            
            # Enum fields
            Optional('location_type'): Or(None, 
                lambda s: s in self.LOCATION_TYPES),
            Optional('activities'): Or(None, str, 
                self._validate_activities),
            
            # Boolean fields
            Optional('is_hidden'): Or(0, 1, bool),
            
            # Timestamp
            Optional('scraped_at'): Or(None, 
                self._validate_timestamp),
            
            # Flexible metadata field
            Optional('metadata'): Or(None, dict),
        })
        
        # Sanitization patterns
        self.sql_injection_patterns = [
            r"(DROP|DELETE|INSERT|UPDATE|SELECT)\s+",
            r"(-{2}|\/\*|\*\/)",  # SQL comments
            r"(;|'|\")\s*(OR|AND)\s*",  # Common injection patterns
        ]
    
    def validate(self, spot_data: dict) -> dict:
        """
        Validate and sanitize spot data
        
        Returns:
            Validated data dict
            
        Raises:
            schema.SchemaError: If validation fails
        """
        # Sanitize strings first
        sanitized = self._sanitize_data(spot_data)
        
        # Validate against schema
        validated = self.schema.validate(sanitized)
        
        # Additional business logic validation
        self._validate_business_rules(validated)
        
        return validated
    
    def _sanitize_data(self, data: dict) -> dict:
        """Sanitize string fields to prevent injection"""
        sanitized = data.copy()
        
        for key, value in sanitized.items():
            if isinstance(value, str):
                # Check for SQL injection patterns
                for pattern in self.sql_injection_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        raise ValueError(
                            f"Potential SQL injection in field '{key}': {value[:50]}..."
                        )
                
                # Basic sanitization
                sanitized[key] = value.strip()
                
                # Escape single quotes for SQL
                if key in ['raw_text', 'extracted_name']:
                    sanitized[key] = value.replace("'", "''")
        
        return sanitized
    
    def _validate_url(self, url: str) -> bool:
        """Validate URL format"""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        return bool(url_pattern.match(url))
    
    def _validate_timestamp(self, timestamp: str) -> bool:
        """Validate ISO format timestamp"""
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return True
        except:
            return False
    
    def _validate_activities(self, activities: str) -> bool:
        """Validate activities string"""
        if not activities:
            return True
            
        # Split by common delimiters
        activity_list = re.split(r'[,;|]', activities.lower())
        
        # Check if at least one activity is valid
        return any(
            any(valid in activity.strip() for valid in self.ACTIVITIES)
            for activity in activity_list
        )
    
    def _validate_business_rules(self, data: dict):
        """Additional business logic validation"""
        # If coordinates exist, both must be present
        has_lat = data.get('latitude') is not None
        has_lon = data.get('longitude') is not None
        
        if has_lat != has_lon:
            raise ValueError(
                "Both latitude and longitude must be provided or both must be None"
            )
        
        # Hidden spots should have location info
        if data.get('is_hidden') and not data.get('location_type'):
            data['location_type'] = 'unknown'
    
    def validate_batch(self, spots: list) -> tuple:
        """
        Validate a batch of spots
        
        Returns:
            (valid_spots, invalid_spots_with_errors)
        """
        valid_spots = []
        invalid_spots = []
        
        for i, spot in enumerate(spots):
            try:
                validated = self.validate(spot)
                valid_spots.append(validated)
            except Exception as e:
                invalid_spots.append({
                    'index': i,
                    'error': str(e),
                    'spot': spot
                })
        
        return valid_spots, invalid_spots


# Example usage
if __name__ == "__main__":
    validator = SpotDataValidator()
    
    # Test valid spot
    valid_spot = {
        'source': 'reddit',
        'source_url': 'https://reddit.com/r/test/123',
        'raw_text': 'Beautiful hidden waterfall near Toulouse',
        'extracted_name': 'Cascade Secrète',
        'latitude': 43.6047,
        'longitude': 1.4442,
        'location_type': 'waterfall',
        'activities': 'baignade, randonnée',
        'is_hidden': 1
    }
    
    # Test invalid spot
    invalid_spot = {
        'source': '',  # Empty source
        'source_url': 'not-a-url',
        'raw_text': "'; DROP TABLE spots; --",  # SQL injection attempt
        'latitude': 50.0,  # Outside bounds
    }
    
    print("Testing valid spot:")
    try:
        result = validator.validate(valid_spot)
        print("✓ Validation passed")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
    
    print("\nTesting invalid spot:")
    try:
        result = validator.validate(invalid_spot)
        print("✓ Validation passed")
    except Exception as e:
        print(f"✗ Validation failed: {e}")