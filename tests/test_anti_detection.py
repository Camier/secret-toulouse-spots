#!/usr/bin/env python3
"""
Unit tests for anti-detection strategies
"""

import pytest
from scrapers.anti_detection import AntiDetectionManager


class TestAntiDetectionManager:
    """Test anti-detection features"""
    
    def setup_method(self):
        """Setup test manager"""
        self.manager = AntiDetectionManager()
    
    @pytest.mark.unit
    def test_browser_fingerprint_generation(self):
        """Test browser fingerprint has required fields"""
        fingerprint = self.manager.generate_browser_fingerprint()
        
        # Check required fields
        assert 'screen' in fingerprint
        assert 'navigator' in fingerprint
        assert 'webgl' in fingerprint
        assert 'timezone' in fingerprint
        
        # Check screen properties
        assert fingerprint['screen']['width'] in [r[0] for r in self.manager.screen_resolutions]
        assert fingerprint['screen']['height'] in [r[1] for r in self.manager.screen_resolutions]
        assert fingerprint['screen']['colorDepth'] in self.manager.color_depths
        
        # Check navigator properties
        assert fingerprint['navigator']['platform'] in self.manager.platforms
        assert isinstance(fingerprint['navigator']['languages'], list)
        assert fingerprint['navigator']['hardwareConcurrency'] in [2, 4, 6, 8, 12, 16]
    
    @pytest.mark.unit
    def test_fingerprint_randomization(self):
        """Test fingerprints are randomized"""
        fingerprints = [self.manager.generate_browser_fingerprint() for _ in range(10)]
        
        # Check that not all fingerprints are identical
        unique_screens = set(str(f['screen']) for f in fingerprints)
        unique_platforms = set(f['navigator']['platform'] for f in fingerprints)
        
        assert len(unique_screens) > 1
        assert len(unique_platforms) > 1
    
    @pytest.mark.unit
    def test_mouse_movement_generation(self):
        """Test mouse movement path generation"""
        start = (100, 100)
        end = (500, 400)
        duration = 1.0
        
        movements = self.manager.generate_mouse_movement(start, end, duration)
        
        # Check path properties
        assert len(movements) > 10  # Should have multiple points
        assert movements[0][0] == pytest.approx(start[0], abs=10)
        assert movements[0][1] == pytest.approx(start[1], abs=10)
        assert movements[-1][0] == pytest.approx(end[0], abs=10)
        assert movements[-1][1] == pytest.approx(end[1], abs=10)
        
        # Check timestamps are increasing
        timestamps = [m[2] for m in movements]
        assert all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))
    
    @pytest.mark.unit
    def test_scroll_pattern_generation(self):
        """Test scroll pattern generation"""
        page_height = 3000
        viewport_height = 800
        
        scroll_pattern = self.manager.generate_scroll_pattern(page_height, viewport_height)
        
        # Check pattern properties
        assert len(scroll_pattern) > 5  # Should have multiple scroll positions
        
        # Check positions are within bounds
        for position, _ in scroll_pattern:
            assert 0 <= position <= page_height - viewport_height
        
        # Check for variety in scrolling (not just down)
        positions = [p[0] for p in scroll_pattern]
        deltas = [positions[i+1] - positions[i] for i in range(len(positions)-1)]
        assert any(d < 0 for d in deltas)  # Some upward scrolling
    
    @pytest.mark.unit
    def test_typing_pattern_generation(self):
        """Test typing pattern generation"""
        text = "Hello world!"
        typing_pattern = self.manager.generate_typing_pattern(text)
        
        # Check basic properties
        assert len(typing_pattern) >= len(text)  # May include typos/corrections
        
        # Check timing increases
        times = [event[1] for event in typing_pattern if event[0] != 'BACKSPACE']
        assert all(times[i] <= times[i+1] for i in range(len(times)-1))
        
        # Check delays are realistic
        for i in range(1, len(typing_pattern)):
            delay = typing_pattern[i][1] - typing_pattern[i-1][1]
            assert 0.05 <= delay <= 2.0  # Reasonable typing speed
    
    @pytest.mark.unit
    def test_request_delays(self):
        """Test request delay generation"""
        delays = [self.manager.apply_request_delays() for _ in range(100)]
        
        # Check delay ranges
        assert all(0.25 <= d <= 240 for d in delays)  # Min possible to max possible
        
        # Check distribution (most should be normal)
        normal_delays = [d for d in delays if 2.0 <= d <= 5.0]
        assert len(normal_delays) > 40  # At least 40% normal browsing
    
    @pytest.mark.unit
    def test_antibot_challenge_detection(self):
        """Test detection of anti-bot challenges"""
        # Test Cloudflare detection
        cf_html = '<div class="cf-browser-verification">Checking your browser...</div>'
        challenges = self.manager.detect_antibot_challenges(cf_html)
        assert challenges['cloudflare'] is True
        
        # Test reCAPTCHA detection
        recaptcha_html = '<div class="g-recaptcha" data-sitekey="key123"></div>'
        challenges = self.manager.detect_antibot_challenges(recaptcha_html)
        assert challenges['recaptcha'] is True
        
        # Test clean page
        clean_html = '<div>Normal content</div>'
        challenges = self.manager.detect_antibot_challenges(clean_html)
        assert not any(challenges.values())
    
    @pytest.mark.unit
    def test_selenium_options(self):
        """Test Selenium options generation"""
        fingerprint = self.manager.generate_browser_fingerprint()
        options = self.manager.get_selenium_options(fingerprint)
        
        # Check required options
        assert '--disable-blink-features=AutomationControlled' in options
        assert any('--window-size=' in opt for opt in options)
        assert any('--user-agent=' in opt for opt in options)
        
        # Check window size matches fingerprint
        window_size_opt = [opt for opt in options if '--window-size=' in opt][0]
        expected = f"--window-size={fingerprint['screen']['width']},{fingerprint['screen']['height']}"
        assert window_size_opt == expected