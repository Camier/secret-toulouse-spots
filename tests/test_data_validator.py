#!/usr/bin/env python3
"""
Unit tests for data validator
"""

import pytest
from scrapers.data_validator import SpotDataValidator


class TestDataValidator:
    """Test spot data validation"""
    
    def setup_method(self):
        """Setup test validator"""
        self.validator = SpotDataValidator()
    
    @pytest.mark.unit
    def test_validate_valid_spot(self, sample_spot_data):
        """Test validation of valid spot data"""
        result = self.validator.validate(sample_spot_data)
        
        assert result is not None
        assert result['latitude'] == 43.6047
        assert result['longitude'] == 1.4442
        assert result['extracted_name'] == "Cascade Secrète"
    
    @pytest.mark.unit
    def test_validate_missing_required_fields(self):
        """Test validation fails for missing required fields"""
        invalid_data = {
            "latitude": 43.6047,
            "longitude": 1.4442
        }
        
        with pytest.raises(Exception):  # Could be ValueError or SchemaError
            self.validator.validate(invalid_data)
    
    @pytest.mark.unit
    def test_validate_invalid_coordinates(self):
        """Test validation of invalid coordinates"""
        # Out of bounds latitude
        invalid_data = {
            "source": "test",
            "source_url": "https://example.com",
            "raw_text": "Test spot with invalid coordinates",
            "latitude": 91.0,  # Invalid
            "longitude": 1.4442
        }
        
        with pytest.raises(Exception):  # Schema validation error
            self.validator.validate(invalid_data)
    
    @pytest.mark.unit
    def test_validate_coordinates_outside_toulouse(self):
        """Test validation rejects coordinates outside Toulouse region"""
        paris_data = {
            "source": "test",
            "source_url": "https://example.com",
            "raw_text": "A spot in Paris, not Toulouse",
            "latitude": 48.8566,  # Paris
            "longitude": 2.3522
        }
        
        with pytest.raises(Exception):  # Schema validation error
            self.validator.validate(paris_data)
    
    @pytest.mark.unit
    def test_normalize_activities(self):
        """Test activity normalization"""
        data = {
            "source": "test",
            "source_url": "https://example.com",
            "raw_text": "Test spot with various activities available",
            "activities": "  swimming, hiking,  picnic  "
        }
        
        result = self.validator.validate(data)
        # Activities should be validated against ACTIVITIES list
        assert "swimming" in result['activities']
        assert "hiking" in result['activities']
        assert "picnic" in result['activities']
    
    @pytest.mark.unit
    def test_confidence_score_validation(self):
        """Test confidence score validation"""
        # Valid confidence score
        data = {
            "source": "test",
            "source_url": "https://example.com",
            "raw_text": "A difficult to access spot requiring climbing skills",
            "confidence_score": 0.8
        }
        result = self.validator.validate(data)
        assert result['confidence_score'] == 0.8
        
        # Invalid confidence score (too high)
        data['confidence_score'] = 1.5
        with pytest.raises(Exception):  # Schema validation error
            self.validator.validate(data)
    
    @pytest.mark.unit
    def test_is_hidden_boolean_conversion(self):
        """Test is_hidden field conversion to integer"""
        data = {
            "source": "test",
            "source_url": "https://example.com",
            "raw_text": "This is a secret hidden spot that few people know about",
            "is_hidden": True
        }
        
        result = self.validator.validate(data)
        assert result['is_hidden'] == 1
        
        data['is_hidden'] = False
        result = self.validator.validate(data)
        assert result['is_hidden'] == 0
    
    @pytest.mark.unit
    def test_metadata_json_validation(self):
        """Test metadata field validation"""
        data = {
            "source": "test",
            "source_url": "https://example.com",
            "raw_text": "Beautiful waterfall spot discovered by a local guide",
            "metadata": {
                "author": "test",
                "tags": ["secret", "waterfall"]
            }
        }
        
        result = self.validator.validate(data)
        assert isinstance(result['metadata'], dict)
        assert result['metadata']['author'] == "test"
        assert "tags" in result['metadata']