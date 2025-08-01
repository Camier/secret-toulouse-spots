#!/usr/bin/env python3
"""
Enhanced coordinate extraction using geopy
Based on Ollama's suggestion for more robust coordinate handling
"""

import re
from typing import Optional, Tuple, List
from decimal import Decimal, InvalidOperation
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import logging

logger = logging.getLogger(__name__)


class EnhancedCoordinateExtractor:
    """Enhanced coordinate extraction with multiple strategies"""
    
    def __init__(self):
        # Initialize geocoder with custom user agent
        self.geocoder = Nominatim(user_agent="SecretToulouseSpots/1.0")
        
        # Enhanced regex patterns (including negative numbers as Ollama suggested)
        self.coord_patterns = [
            # Decimal degrees with optional negative
            r'(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)',
            # Degrees with symbols (including minutes notation)
            r'(\d+)°\s*(\d+)?\'?\s*([NS])[,\s]+(\d+)°\s*(\d+)?\'?\s*([EW])',
            # Simple degrees with symbols
            r'(\d+\.?\d*)°\s*([NS])[,\s]+(\d+\.?\d*)°\s*([EW])',
            # French format with comma as decimal
            r'(-?\d+,\d+)[;\s]+(-?\d+,\d+)',
            # With labels (fixed to handle colon with no space)
            r'lat:?\s*(-?\d+\.?\d*)\s+long?:?\s*(-?\d+\.?\d*)',
            # Alternative label format
            r'latitude[:\s]+(-?\d+\.\d+).*?longitude[:\s]+(-?\d+\.\d+)',
        ]
        
        # Toulouse region bounds for validation
        self.toulouse_bounds = {
            'min_lat': 42.5,
            'max_lat': 44.5,
            'min_lon': -1.0,
            'max_lon': 3.0
        }
    
    def extract_from_text(self, text: str) -> Optional[Tuple[float, float]]:
        """
        Extract coordinates from text using multiple methods
        
        Returns:
            Tuple of (latitude, longitude) or None
        """
        # Try regex extraction first
        coords = self._extract_with_regex(text)
        if coords:
            return coords
            
        # Try geocoding location names
        coords = self._extract_with_geocoding(text)
        if coords:
            return coords
            
        return None
    
    def _extract_with_regex(self, text: str) -> Optional[Tuple[float, float]]:
        """Extract coordinates using regex patterns"""
        for pattern in self.coord_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    coords = self._parse_match(match)
                    if coords and self._validate_coordinates(*coords):
                        return coords
                except (ValueError, InvalidOperation):
                    continue
                    
        return None
    
    def _parse_match(self, match: tuple) -> Optional[Tuple[float, float]]:
        """Parse regex match into coordinates"""
        if len(match) == 2:
            # Simple decimal format
            lat = float(match[0].replace(',', '.'))
            lon = float(match[1].replace(',', '.'))
            return lat, lon
            
        elif len(match) == 4:
            # Degrees with direction
            lat = float(match[0])
            if match[1].upper() == 'S':
                lat = -lat
            lon = float(match[2])
            if match[3].upper() == 'W':
                lon = -lon
            return lat, lon
            
        elif len(match) == 6:
            # Degrees and minutes with direction
            lat_deg = float(match[0])
            lat_min = float(match[1]) if match[1] else 0
            lat = lat_deg + lat_min / 60
            if match[2].upper() == 'S':
                lat = -lat
                
            lon_deg = float(match[3])
            lon_min = float(match[4]) if match[4] else 0
            lon = lon_deg + lon_min / 60
            if match[5].upper() == 'W':
                lon = -lon
            return lat, lon
            
        return None
    
    def _extract_with_geocoding(self, text: str) -> Optional[Tuple[float, float]]:
        """Extract coordinates by geocoding location names"""
        # Extract potential location names
        location_patterns = [
            r'(?:à|au|aux|près de|proche de)\s+([A-Z][a-zÀ-ÿ\-\s]+)',
            r'(?:cascade|grotte|lac|château)\s+(?:de|d\')\s+([A-Z][a-zÀ-ÿ\-\s]+)',
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text)
            for location in matches:
                # Add region context
                query = f"{location}, Haute-Garonne, France"
                try:
                    result = self.geocoder.geocode(query, timeout=5)
                    if result:
                        lat, lon = result.latitude, result.longitude
                        if self._validate_coordinates(lat, lon):
                            logger.info(f"Geocoded '{location}' to {lat}, {lon}")
                            return lat, lon
                except (GeocoderTimedOut, GeocoderServiceError) as e:
                    logger.warning(f"Geocoding error for '{location}': {e}")
                    
        return None
    
    def _validate_coordinates(self, lat: float, lon: float) -> bool:
        """Validate coordinates are within Toulouse region"""
        return (self.toulouse_bounds['min_lat'] <= lat <= self.toulouse_bounds['max_lat'] and
                self.toulouse_bounds['min_lon'] <= lon <= self.toulouse_bounds['max_lon'])
    
    def extract_all_coordinates(self, text: str) -> List[Tuple[float, float]]:
        """Extract all valid coordinates from text"""
        coords_set = set()
        
        # Try all regex patterns
        for pattern in self.coord_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    coords = self._parse_match(match)
                    if coords and self._validate_coordinates(*coords):
                        coords_set.add(coords)
                except (ValueError, InvalidOperation):
                    continue
        
        return list(coords_set)
    
    def validate_and_normalize(self, lat: str, lon: str) -> Optional[Tuple[float, float]]:
        """
        Validate and normalize coordinate strings
        Using Decimal for precision as Ollama suggested
        """
        try:
            # Use Decimal for accurate parsing
            lat_decimal = Decimal(lat.replace(',', '.'))
            lon_decimal = Decimal(lon.replace(',', '.'))
            
            # Convert to float for validation
            lat_float = float(lat_decimal)
            lon_float = float(lon_decimal)
            
            if self._validate_coordinates(lat_float, lon_float):
                return lat_float, lon_float
                
        except (InvalidOperation, ValueError) as e:
            logger.error(f"Invalid coordinate format: {lat}, {lon} - {e}")
            
        return None


# Example usage
if __name__ == "__main__":
    extractor = EnhancedCoordinateExtractor()
    
    test_texts = [
        "Belle cascade près de Saint-Béat, coordonnées: 42.7921, 0.6908",
        "Grotte secrète à 43.123,-0.456",
        "Lac caché 43°36'N 1°26'E",
        "Château abandonné de Montréjeau",
        "Position GPS: lat:43.6047 long:1.4442",
    ]
    
    for text in test_texts:
        coords = extractor.extract_from_text(text)
        if coords:
            print(f"✓ Found: {coords} from '{text[:50]}...'")
        else:
            print(f"✗ No coordinates in '{text[:50]}...'")