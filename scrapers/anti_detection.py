#!/usr/bin/env python3
"""
Advanced anti-detection strategies for web scraping
Implements browser fingerprint randomization, realistic behavior patterns
"""

import random
import time
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


class AntiDetectionManager:
    """Advanced anti-detection techniques for web scraping"""
    
    def __init__(self):
        # Browser fingerprint components
        self.screen_resolutions = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1280, 720), (1600, 900), (2560, 1440), (3840, 2160)
        ]
        
        self.color_depths = [24, 32]
        
        self.languages = [
            ['fr-FR', 'fr', 'en-US', 'en'],
            ['en-US', 'en'],
            ['fr-FR', 'fr'],
            ['es-ES', 'es', 'en'],
            ['de-DE', 'de', 'en']
        ]
        
        self.platforms = [
            'Win32', 'Win64', 'MacIntel', 'Linux x86_64'
        ]
        
        self.webgl_vendors = [
            'Intel Inc.', 'NVIDIA Corporation', 'AMD', 'Apple Inc.'
        ]
        
        self.webgl_renderers = [
            'Intel Iris OpenGL Engine',
            'NVIDIA GeForce GTX 1060/PCIe/SSE2',
            'AMD Radeon Pro 5300M OpenGL Engine',
            'Apple M1'
        ]
        
        # Canvas fingerprint noise
        self.canvas_noise_level = 0.0001
        
    def generate_browser_fingerprint(self) -> Dict:
        """Generate a realistic browser fingerprint"""
        resolution = random.choice(self.screen_resolutions)
        
        platform = random.choice(self.platforms)
        
        fingerprint = {
            'screen': {
                'width': resolution[0],
                'height': resolution[1],
                'availWidth': resolution[0],
                'availHeight': resolution[1] - random.randint(40, 100),  # Taskbar
                'colorDepth': random.choice(self.color_depths),
                'pixelDepth': random.choice(self.color_depths)
            },
            'navigator': {
                'language': random.choice(self.languages)[0],
                'languages': random.choice(self.languages),
                'platform': platform,
                'hardwareConcurrency': random.choice([2, 4, 6, 8, 12, 16]),
                'deviceMemory': random.choice([4, 8, 16, 32]),
                'maxTouchPoints': 0 if 'Win' in platform else random.choice([0, 1, 5])
            },
            'webgl': {
                'vendor': random.choice(self.webgl_vendors),
                'renderer': random.choice(self.webgl_renderers)
            },
            'timezone': random.choice([
                'Europe/Paris', 'Europe/London', 'Europe/Berlin',
                'America/New_York', 'America/Los_Angeles'
            ]),
            'plugins': self._generate_plugins(),
            'canvas_noise': self.canvas_noise_level
        }
        
        return fingerprint
        
    def _generate_plugins(self) -> List[Dict]:
        """Generate realistic browser plugins"""
        available_plugins = [
            {'name': 'Chrome PDF Plugin', 'filename': 'internal-pdf-viewer'},
            {'name': 'Chrome PDF Viewer', 'filename': 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
            {'name': 'Native Client', 'filename': 'internal-nacl-plugin'},
            {'name': 'Shockwave Flash', 'filename': 'pepflashplayer.dll'},
        ]
        
        # Randomly select 0-3 plugins
        num_plugins = random.randint(0, min(3, len(available_plugins)))
        return random.sample(available_plugins, num_plugins)
        
    def inject_fingerprint_to_selenium(self, driver, fingerprint: Dict):
        """Inject fingerprint into Selenium WebDriver"""
        # Override navigator properties
        script = """
        Object.defineProperty(navigator, 'languages', {
            get: function() { return %s; }
        });
        Object.defineProperty(navigator, 'language', {
            get: function() { return '%s'; }
        });
        Object.defineProperty(navigator, 'platform', {
            get: function() { return '%s'; }
        });
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: function() { return %d; }
        });
        Object.defineProperty(navigator, 'deviceMemory', {
            get: function() { return %d; }
        });
        Object.defineProperty(screen, 'width', {
            get: function() { return %d; }
        });
        Object.defineProperty(screen, 'height', {
            get: function() { return %d; }
        });
        """ % (
            json.dumps(fingerprint['navigator']['languages']),
            fingerprint['navigator']['language'],
            fingerprint['navigator']['platform'],
            fingerprint['navigator']['hardwareConcurrency'],
            fingerprint['navigator']['deviceMemory'],
            fingerprint['screen']['width'],
            fingerprint['screen']['height']
        )
        
        driver.execute_script(script)
        
    def generate_mouse_movement(self, 
                              start: Tuple[int, int], 
                              end: Tuple[int, int], 
                              duration: float = 1.0) -> List[Tuple[int, int, float]]:
        """Generate realistic mouse movement path with timestamps"""
        points = []
        
        # Number of intermediate points
        num_points = int(duration * 60)  # 60 points per second
        
        # Generate control points for bezier curve
        control1 = (
            start[0] + random.randint(-50, 50),
            start[1] + random.randint(-50, 50)
        )
        control2 = (
            end[0] + random.randint(-50, 50),
            end[1] + random.randint(-50, 50)
        )
        
        # Generate bezier curve points
        for i in range(num_points):
            t = i / num_points
            
            # Cubic bezier formula
            x = (1-t)**3 * start[0] + \
                3*(1-t)**2*t * control1[0] + \
                3*(1-t)*t**2 * control2[0] + \
                t**3 * end[0]
                
            y = (1-t)**3 * start[1] + \
                3*(1-t)**2*t * control1[1] + \
                3*(1-t)*t**2 * control2[1] + \
                t**3 * end[1]
                
            # Add small random noise
            x += random.gauss(0, 2)
            y += random.gauss(0, 2)
            
            # Timestamp with slight variation
            timestamp = (i / num_points) * duration
            timestamp += random.gauss(0, 0.01)
            
            points.append((int(x), int(y), timestamp))
            
        return points
        
    def generate_scroll_pattern(self, 
                              page_height: int, 
                              viewport_height: int) -> List[Tuple[int, float]]:
        """Generate realistic scroll pattern"""
        positions = []
        current_pos = 0
        current_time = 0.0
        
        while current_pos < page_height - viewport_height:
            # Read time (varies based on content)
            read_time = random.gauss(3.0, 1.0)
            read_time = max(0.5, min(read_time, 10.0))
            
            # Scroll distance (varies)
            scroll_distance = random.randint(100, 500)
            
            # Sometimes scroll back up a bit
            if random.random() < 0.1:
                scroll_distance = -random.randint(50, 200)
                
            # Calculate new position
            new_pos = current_pos + scroll_distance
            new_pos = max(0, min(new_pos, page_height - viewport_height))
            
            # Add intermediate positions for smooth scrolling
            steps = 10
            for i in range(steps):
                intermediate_pos = current_pos + (new_pos - current_pos) * (i / steps)
                intermediate_time = current_time + (read_time / steps) * i
                positions.append((int(intermediate_pos), intermediate_time))
                
            current_pos = new_pos
            current_time += read_time
            
            # Sometimes pause for longer (reading interesting content)
            if random.random() < 0.2:
                current_time += random.gauss(5.0, 2.0)
                
        return positions
        
    def generate_typing_pattern(self, text: str) -> List[Tuple[str, float]]:
        """Generate realistic typing pattern with timing"""
        events = []
        current_time = 0.0
        
        for char in text:
            # Typing speed varies
            if char == ' ':
                delay = random.gauss(0.15, 0.05)
            elif char in '.,!?':
                delay = random.gauss(0.3, 0.1)
            else:
                delay = random.gauss(0.1, 0.03)
                
            delay = max(0.05, min(delay, 0.5))
            current_time += delay
            
            events.append((char, current_time))
            
            # Occasional pauses (thinking)
            if random.random() < 0.05:
                current_time += random.gauss(1.0, 0.3)
                
            # Typos and corrections
            if random.random() < 0.02 and len(events) > 2:
                # Backspace
                events.append(('BACKSPACE', current_time + 0.1))
                events.append(('BACKSPACE', current_time + 0.2))
                # Retype
                events.append((events[-3][0], current_time + 0.3))
                current_time += 0.4
                
        return events
        
    def apply_request_delays(self) -> float:
        """Generate realistic request delays"""
        # Human-like browsing patterns
        patterns = [
            ('fast', 0.5, 2.0),    # Quick browsing
            ('normal', 2.0, 5.0),  # Normal reading
            ('slow', 5.0, 15.0),   # Careful reading
            ('break', 30.0, 120.0) # Taking a break
        ]
        
        # Weight towards normal behavior
        weights = [0.2, 0.6, 0.15, 0.05]
        pattern = random.choices(patterns, weights=weights)[0]
        
        delay = random.uniform(pattern[1], pattern[2])
        
        # Add some randomness
        if random.random() < 0.1:  # 10% chance of unusual delay
            delay *= random.uniform(0.5, 2.0)
            
        return delay
        
    def detect_antibot_challenges(self, page_source: str) -> Dict[str, bool]:
        """Detect common anti-bot challenges"""
        challenges = {
            'cloudflare': any(marker in page_source.lower() for marker in [
                'cloudflare', 'cf-browser-verification', 'cf-challenge'
            ]),
            'recaptcha': 'g-recaptcha' in page_source or 'grecaptcha' in page_source,
            'hcaptcha': 'h-captcha' in page_source or 'hcaptcha' in page_source,
            'datadome': 'datadome' in page_source.lower(),
            'perimeter': 'px-captcha' in page_source or 'perimeterx' in page_source.lower(),
            'incapsula': 'incapsula' in page_source.lower() or '_incap_' in page_source,
            'akamai': 'akamai' in page_source.lower()
        }
        
        return challenges
        
    def get_selenium_options(self, fingerprint: Dict) -> List[str]:
        """Get Selenium Chrome options for anti-detection"""
        options = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            f'--window-size={fingerprint["screen"]["width"]},{fingerprint["screen"]["height"]}',
            f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--disable-gpu',
            '--disable-logging',
            '--disable-software-rasterizer',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding'
        ]
        
        # Add random flags that real users might have
        if random.random() < 0.3:
            options.append('--enable-automation')
            
        if random.random() < 0.5:
            options.append('--start-maximized')
            
        return options


# Example usage
class StealthScraper:
    """Example scraper using anti-detection techniques"""
    
    def __init__(self):
        self.anti_detect = AntiDetectionManager()
        self.fingerprint = self.anti_detect.generate_browser_fingerprint()
        
    def scrape_with_selenium(self, url: str):
        """Scrape using Selenium with anti-detection"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.action_chains import ActionChains
        
        # Setup Chrome options
        chrome_options = Options()
        for opt in self.anti_detect.get_selenium_options(self.fingerprint):
            chrome_options.add_argument(opt)
            
        # Disable automation flags
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Create driver
        driver = webdriver.Chrome(options=chrome_options)
        
        # Inject fingerprint
        self.anti_detect.inject_fingerprint_to_selenium(driver, self.fingerprint)
        
        # Navigate with realistic behavior
        driver.get(url)
        
        # Wait like a human
        time.sleep(self.anti_detect.apply_request_delays())
        
        # Check for anti-bot challenges
        challenges = self.anti_detect.detect_antibot_challenges(driver.page_source)
        if any(challenges.values()):
            logger.warning(f"Detected anti-bot challenges: {challenges}")
            
        # Simulate human behavior
        self._simulate_human_behavior(driver)
        
        return driver
        
    def _simulate_human_behavior(self, driver):
        """Simulate realistic human behavior"""
        actions = ActionChains(driver)
        
        # Random mouse movements
        for _ in range(random.randint(2, 5)):
            start = (random.randint(100, 500), random.randint(100, 500))
            end = (random.randint(100, 500), random.randint(100, 500))
            
            path = self.anti_detect.generate_mouse_movement(start, end)
            
            for x, y, _ in path:
                actions.move_by_offset(x - actions._pointer_location['x'], 
                                     y - actions._pointer_location['y'])
                
        actions.perform()
        
        # Realistic scrolling
        viewport_height = driver.execute_script("return window.innerHeight")
        page_height = driver.execute_script("return document.body.scrollHeight")
        
        scroll_pattern = self.anti_detect.generate_scroll_pattern(
            page_height, viewport_height
        )
        
        for position, _ in scroll_pattern[:10]:  # Limit scrolling
            driver.execute_script(f"window.scrollTo(0, {position})")
            time.sleep(random.uniform(0.1, 0.3))