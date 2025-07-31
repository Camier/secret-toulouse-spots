#!/usr/bin/env python3
"""
Secure Instagram scraper for French outdoor spots
Uses environment variables or keyring for credentials
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import time
import sqlite3
from typing import List, Dict, Optional
import logging

try:
    from instagrapi import Client
except ImportError:
    print("Error: instagrapi not installed. Run: pip install instagrapi")
    sys.exit(1)

# Try to import config, fallback to environment variables
try:
    from config import INSTAGRAM_CONFIG, SCRAPING_CONFIG, SECURITY_CONFIG
except ImportError:
    # Fallback configuration
    INSTAGRAM_CONFIG = {
        'username': os.getenv('INSTAGRAM_USERNAME', ''),
        'password': os.getenv('INSTAGRAM_PASSWORD', ''),
        'session_file': Path.home() / '.config' / 'weather-app' / 'instagram_session.json',
        'delay_range': [3, 7]
    }
    SCRAPING_CONFIG = {
        'instagram_hashtags': ['randonnee', 'baignadesauvage', 'cascadefrance']
    }
    SECURITY_CONFIG = {
        'session_file_permissions': 0o600,
        'enable_logging': True
    }

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SecureInstagramScraper:
    """Secure Instagram scraper with proper credential management"""
    
    def __init__(self):
        self.cl = Client()
        self.cl.delay_range = INSTAGRAM_CONFIG['delay_range']
        self.session_file = Path(INSTAGRAM_CONFIG['session_file'])
        self.db_path = "hidden_spots.db"
        self.hashtags = SCRAPING_CONFIG['instagram_hashtags']
        
        # Ensure secure directory structure
        self._ensure_secure_directories()
        
        # Water and hidden keywords
        self.water_keywords = [
            'cascade', 'lac', 'source', 'rivière', 'baignade', 
            'piscine naturelle', 'vasque', 'torrent', 'ruisseau'
        ]
        self.hidden_keywords = [
            'secret', 'caché', 'peu connu', 'sauvage', 'préservé',
            'hors des sentiers', 'méconnu', 'confidentiel'
        ]
    
    def _ensure_secure_directories(self):
        """Create secure directories for config and session files"""
        config_dir = self.session_file.parent
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Set secure permissions on config directory
        try:
            os.chmod(config_dir, 0o700)  # rwx for owner only
        except:
            logger.warning("Could not set secure permissions on config directory")
    
    def _get_credentials(self) -> tuple:
        """Get credentials from environment or keyring"""
        username = INSTAGRAM_CONFIG['username']
        password = INSTAGRAM_CONFIG['password']
        
        if not username or not password:
            # Try keyring as fallback
            try:
                import keyring
                username = username or keyring.get_password('weather-app', 'instagram_username')
                password = password or keyring.get_password('weather-app', 'instagram_password')
            except ImportError:
                pass
        
        if not username or not password:
            logger.error("Instagram credentials not found!")
            print("\nPlease set credentials using one of these methods:")
            print("1. Environment variables:")
            print("   export INSTAGRAM_USERNAME='your_username'")
            print("   export INSTAGRAM_PASSWORD='your_password'")
            print("\n2. Or use keyring:")
            print("   pip install keyring")
            print("   keyring set weather-app instagram_username")
            print("   keyring set weather-app instagram_password")
            sys.exit(1)
        
        return username, password
    
    def _secure_session_file(self):
        """Set secure permissions on session file"""
        if self.session_file.exists():
            try:
                os.chmod(self.session_file, SECURITY_CONFIG['session_file_permissions'])
                logger.info("Secured session file permissions")
            except:
                logger.warning("Could not secure session file permissions")
    
    def login(self) -> bool:
        """Login to Instagram with secure credential handling"""
        try:
            # Try loading session first
            if self.session_file.exists():
                try:
                    self.cl.load_settings(self.session_file)
                    self.cl.account_info()  # Verify session
                    logger.info("Loaded existing session")
                    return True
                except:
                    logger.info("Session expired, logging in again...")
            
            # Get credentials securely
            username, password = self._get_credentials()
            
            logger.info(f"Logging in as {username}...")
            self.cl.login(username, password)
            
            # Save session securely
            self.cl.dump_settings(self.session_file)
            self._secure_session_file()
            
            logger.info("Login successful!")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def scrape_hashtag(self, hashtag: str, amount: int = 20) -> List[Dict]:
        """Scrape posts from a hashtag with error handling"""
        logger.info(f"Searching #{hashtag}...")
        posts_data = []
        
        try:
            # Get hashtag info
            info = self.cl.hashtag_info(hashtag)
            logger.info(f"Found {info.media_count:,} total posts")
            
            # Try to get posts
            try:
                medias = self.cl.hashtag_medias_recent(hashtag, amount=amount)
            except:
                logger.warning("Recent posts failed, trying top posts...")
                medias = self.cl.hashtag_medias_top(hashtag, amount=9)
            
            # Process posts
            for media in medias:
                try:
                    caption = getattr(media, 'caption_text', '')
                    
                    post_data = {
                        'hashtag': hashtag,
                        'post_id': str(media.pk) if hasattr(media, 'pk') else None,
                        'caption': caption[:1000] if caption else '',
                        'username': media.user.username if hasattr(media, 'user') else None,
                        'timestamp': media.taken_at if hasattr(media, 'taken_at') else None,
                        'location': None,
                        'is_water_related': self._is_water_related(caption),
                        'is_hidden': self._is_hidden_spot(caption)
                    }
                    
                    # Extract location
                    if hasattr(media, 'location') and media.location:
                        try:
                            post_data['location'] = {
                                'name': media.location.name,
                                'lat': media.location.lat,
                                'lng': media.location.lng
                            }
                        except:
                            pass
                    
                    posts_data.append(post_data)
                    
                except Exception as e:
                    logger.warning(f"Error processing post: {type(e).__name__}")
                    continue
            
            logger.info(f"Retrieved {len(posts_data)} posts from #{hashtag}")
            
        except Exception as e:
            logger.error(f"Error searching hashtag: {e}")
        
        return posts_data
    
    def _is_water_related(self, text: str) -> bool:
        """Check if text mentions water spots"""
        if not text:
            return False
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.water_keywords)
    
    def _is_hidden_spot(self, text: str) -> bool:
        """Check if text indicates a hidden spot"""
        if not text:
            return False
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.hidden_keywords)
    
    def save_to_database(self, posts: List[Dict]):
        """Save posts to database with proper error handling"""
        if not posts:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved = 0
        for post in posts:
            try:
                # Only save relevant posts
                if not (post['is_water_related'] or post['is_hidden']):
                    continue
                
                # Extract location data
                lat = lng = location_name = None
                if post['location']:
                    lat = post['location']['lat']
                    lng = post['location']['lng']
                    location_name = post['location']['name']
                
                # Save to database
                cursor.execute("""
                    INSERT OR IGNORE INTO instagram_posts
                    (post_id, username, caption, hashtags, location_name, 
                     latitude, longitude, post_date, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    post['post_id'],
                    post['username'],
                    post['caption'],
                    '#' + post['hashtag'],
                    location_name,
                    lat,
                    lng,
                    post['timestamp'].isoformat() if post['timestamp'] else None,
                    datetime.now().isoformat()
                ))
                
                if cursor.rowcount > 0:
                    saved += 1
                
            except Exception as e:
                logger.error(f"Error saving post: {e}")
        
        conn.commit()
        conn.close()
        
        logger.info(f"Saved {saved} relevant posts to database")
    
    def run_full_scrape(self):
        """Run the full scraping pipeline"""
        logger.info("Starting French Outdoor Instagram Scraper")
        
        all_posts = []
        
        for i, hashtag in enumerate(self.hashtags):
            posts = self.scrape_hashtag(hashtag, amount=15)
            all_posts.extend(posts)
            
            # Save progress
            self.save_to_database(posts)
            
            # Rate limiting
            if i < len(self.hashtags) - 1:
                wait_time = 5
                logger.info(f"Waiting {wait_time}s for rate limiting...")
                time.sleep(wait_time)
        
        return all_posts


def main():
    """Main execution with proper error handling"""
    scraper = SecureInstagramScraper()
    
    try:
        if scraper.login():
            posts = scraper.run_full_scrape()
            logger.info(f"Scraping complete! Processed {len(posts)} posts")
        else:
            logger.error("Could not authenticate with Instagram")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()