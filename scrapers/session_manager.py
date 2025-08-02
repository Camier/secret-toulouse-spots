#!/usr/bin/env python3
"""
Session persistence manager for scrapers
Handles cookies, headers, and authentication state
"""

import json
import pickle
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import requests
from requests.cookies import RequestsCookieJar

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages persistent sessions across scraper runs"""
    
    def __init__(self, 
                 session_name: str,
                 session_dir: str = "sessions",
                 expire_hours: int = 24):
        """
        Initialize session manager
        
        Args:
            session_name: Unique name for this session (e.g., 'instagram', 'reddit')
            session_dir: Directory to store session files
            expire_hours: Hours before session expires
        """
        self.session_name = session_name
        self.session_dir = Path(session_dir)
        self.expire_hours = expire_hours
        
        # Create session directory if it doesn't exist
        self.session_dir.mkdir(exist_ok=True)
        
        # Define file paths
        self.cookie_file = self.session_dir / f"{session_name}_cookies.pkl"
        self.header_file = self.session_dir / f"{session_name}_headers.json"
        self.state_file = self.session_dir / f"{session_name}_state.json"
        
    def save_session(self, session: requests.Session, additional_state: Dict = None):
        """Save session cookies, headers, and state"""
        try:
            # Save cookies
            with open(self.cookie_file, 'wb') as f:
                pickle.dump(session.cookies, f)
                
            # Save headers (convert to dict for JSON serialization)
            headers = dict(session.headers)
            with open(self.header_file, 'w') as f:
                json.dump(headers, f, indent=2)
                
            # Save additional state
            state = {
                'timestamp': datetime.now().isoformat(),
                'expire_at': (datetime.now() + timedelta(hours=self.expire_hours)).isoformat(),
                'session_name': self.session_name,
                'additional_state': additional_state or {}
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
            logger.info(f"Session '{self.session_name}' saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False
            
    def load_session(self, session: requests.Session) -> Optional[Dict]:
        """Load saved session into requests session object"""
        try:
            # Check if session exists and is not expired
            if not self._is_valid_session():
                logger.info("No valid session found")
                return None
                
            # Load cookies
            if self.cookie_file.exists():
                with open(self.cookie_file, 'rb') as f:
                    cookies = pickle.load(f)
                    session.cookies.update(cookies)
                    
            # Load headers
            if self.header_file.exists():
                with open(self.header_file, 'r') as f:
                    headers = json.load(f)
                    session.headers.update(headers)
                    
            # Load state
            state = None
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    
            logger.info(f"Session '{self.session_name}' loaded successfully")
            return state.get('additional_state', {}) if state else {}
            
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None
            
    def _is_valid_session(self) -> bool:
        """Check if saved session exists and is not expired"""
        if not all([self.cookie_file.exists(), self.state_file.exists()]):
            return False
            
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                
            expire_time = datetime.fromisoformat(state['expire_at'])
            is_valid = datetime.now() < expire_time
            
            if not is_valid:
                logger.info(f"Session expired at {expire_time}")
                
            return is_valid
            
        except Exception as e:
            logger.error(f"Error checking session validity: {e}")
            return False
            
    def clear_session(self):
        """Clear all saved session data"""
        for file in [self.cookie_file, self.header_file, self.state_file]:
            if file.exists():
                file.unlink()
                
        logger.info(f"Session '{self.session_name}' cleared")
        
    def get_session_info(self) -> Optional[Dict]:
        """Get information about the saved session"""
        if not self.state_file.exists():
            return None
            
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                
            # Calculate remaining time
            expire_time = datetime.fromisoformat(state['expire_at'])
            remaining = expire_time - datetime.now()
            
            return {
                'session_name': self.session_name,
                'created_at': state['timestamp'],
                'expires_at': state['expire_at'],
                'is_valid': remaining.total_seconds() > 0,
                'remaining_hours': remaining.total_seconds() / 3600,
                'has_cookies': self.cookie_file.exists(),
                'has_headers': self.header_file.exists(),
                'additional_state': state.get('additional_state', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return None


class CookieManager:
    """Specialized cookie management for browser automation"""
    
    def __init__(self, cookie_file: str = 'cookies.pkl'):
        self.cookie_file = Path(cookie_file)
        
    def save_cookies(self, driver):
        """Save cookies from Selenium WebDriver"""
        try:
            cookies = driver.get_cookies()
            with open(self.cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
            logger.info(f"Saved {len(cookies)} cookies")
            return True
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            return False
            
    def load_cookies(self, driver):
        """Load cookies into Selenium WebDriver"""
        if not self.cookie_file.exists():
            logger.info("No saved cookies found")
            return False
            
        try:
            with open(self.cookie_file, 'rb') as f:
                cookies = pickle.load(f)
                
            # Navigate to domain first (required for adding cookies)
            current_url = driver.current_url
            if 'about:blank' in current_url or not current_url:
                logger.warning("Navigate to target domain before loading cookies")
                return False
                
            # Add each cookie
            for cookie in cookies:
                try:
                    # Remove expiry if it's in the past
                    if 'expiry' in cookie:
                        if cookie['expiry'] < datetime.now().timestamp():
                            continue
                            
                    driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"Failed to add cookie: {e}")
                    
            logger.info(f"Loaded {len(cookies)} cookies")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return False
            
    def clear_cookies(self):
        """Clear saved cookies"""
        if self.cookie_file.exists():
            self.cookie_file.unlink()
            logger.info("Cookies cleared")


# Example usage patterns
def example_usage():
    """Example of how to use session persistence"""
    
    # For requests-based scrapers
    session = requests.Session()
    manager = SessionManager('reddit')
    
    # Try to load existing session
    state = manager.load_session(session)
    if state:
        print(f"Loaded session with state: {state}")
    else:
        # Create new session
        session.headers.update({
            'User-Agent': 'MyBot/1.0'
        })
        # After successful login...
        manager.save_session(session, {'username': 'user123'})
        
    # For Selenium-based scrapers
    from selenium import webdriver
    driver = webdriver.Chrome()
    cookie_mgr = CookieManager('instagram_cookies.pkl')
    
    # Navigate to site first
    driver.get('https://instagram.com')
    
    # Try to load cookies
    if cookie_mgr.load_cookies(driver):
        driver.refresh()  # Refresh to use loaded cookies
    else:
        # Do login process...
        # Then save cookies
        cookie_mgr.save_cookies(driver)