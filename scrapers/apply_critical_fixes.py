#!/usr/bin/env python3
"""
Apply critical fixes identified in the official documentation gap analysis
Run this script to automatically fix the most critical issues
"""

import os
import re
from pathlib import Path


def fix_beautifulsoup_parsers():
    """Add explicit parser to all BeautifulSoup instantiations"""
    print("🔧 Fixing BeautifulSoup parser specifications...")
    
    patterns = [
        (r'BeautifulSoup\(([^,\)]+)\)', r'BeautifulSoup(\1, "lxml")'),
        (r'BeautifulSoup\(([^,\)]+),\s*[\'"]html\.parser[\'"]\)', r'BeautifulSoup(\1, "lxml")'),
    ]
    
    files_fixed = 0
    for py_file in Path(".").glob("*.py"):
        content = py_file.read_text()
        original = content
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
            
        if content != original:
            py_file.write_text(content)
            files_fixed += 1
            print(f"  ✅ Fixed {py_file.name}")
            
    print(f"  Fixed {files_fixed} files\n")


def fix_requests_timeouts():
    """Add timeout to all requests calls"""
    print("🔧 Adding timeouts to requests calls...")
    
    patterns = [
        (r'requests\.get\(([^)]+)\)', r'requests.get(\1, timeout=30)'),
        (r'requests\.post\(([^)]+)\)', r'requests.post(\1, timeout=30)'),
        (r'self\.session\.get\(([^)]+)\)', r'self.session.get(\1, timeout=30)'),
        (r'self\.session\.post\(([^)]+)\)', r'self.session.post(\1, timeout=30)'),
    ]
    
    # Don't add timeout if already present
    def replace_if_no_timeout(match):
        if 'timeout' not in match.group(0):
            return match.group(0).replace(')', ', timeout=30)')
        return match.group(0)
    
    files_fixed = 0
    for py_file in Path(".").glob("*.py"):
        content = py_file.read_text()
        original = content
        
        # Find all requests calls and add timeout if missing
        content = re.sub(r'requests\.(get|post)\([^)]+\)', replace_if_no_timeout, content)
        content = re.sub(r'self\.session\.(get|post)\([^)]+\)', replace_if_no_timeout, content)
        
        if content != original:
            py_file.write_text(content)
            files_fixed += 1
            print(f"  ✅ Fixed {py_file.name}")
            
    print(f"  Fixed {files_fixed} files\n")


def fix_response_validation():
    """Add response.raise_for_status() after requests calls"""
    print("🔧 Adding response validation...")
    
    files_fixed = 0
    for py_file in Path(".").glob("*.py"):
        lines = py_file.read_text().splitlines()
        new_lines = []
        
        for i, line in enumerate(lines):
            new_lines.append(line)
            
            # If line contains a requests call that returns a response
            if ('response = ' in line or 'resp = ' in line) and ('requests.' in line or 'session.' in line):
            response.raise_for_status()
                indent = len(line) - len(line.lstrip())
                # Add raise_for_status on next line with same indentation
                new_lines.append(' ' * indent + 'response.raise_for_status()')
                
        if len(new_lines) != len(lines):
            py_file.write_text('\n'.join(new_lines))
            files_fixed += 1
            print(f"  ✅ Fixed {py_file.name}")
            
    print(f"  Fixed {files_fixed} files\n")


def add_selenium_cleanup():
    """Add proper cleanup for Selenium drivers"""
    print("🔧 Adding Selenium driver cleanup...")
    
    forum_scraper = Path("forum_scraper.py")
    if forum_scraper.exists():
        content = forum_scraper.read_text()
        
        # Add context manager methods if not present
        if "__enter__" not in content:
            # Find the class definition
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if "class FrenchOutdoorForumScraper" in line:
                    # Find the end of __init__ method
                    for j in range(i, len(lines)):
                        if lines[j].strip() == "" and j > i + 10:
                            # Insert context manager methods
                            lines.insert(j, "    def __enter__(self):")
                            lines.insert(j + 1, "        self.setup_driver()")
                            lines.insert(j + 2, "        return self")
                            lines.insert(j + 3, "")
                            lines.insert(j + 4, "    def __exit__(self, exc_type, exc_val, exc_tb):")
                            lines.insert(j + 5, "        if self.driver:")
                            lines.insert(j + 6, "            self.driver.quit()")
                            lines.insert(j + 7, "")
                            break
                    break
            
            forum_scraper.write_text('\n'.join(lines))
            print(f"  ✅ Added context manager to forum_scraper.py")
    
    print()


def create_config_file():
    """Create a configuration file template"""
    print("🔧 Creating configuration template...")
    
    config_dir = Path("../config")
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / "scraper_config.py"
    if not config_file.exists():
        config_file.write_text('''"""
Scraper configuration settings
Load from environment variables with sensible defaults
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScraperConfig:
    # Reddit settings
    reddit_client_id: Optional[str] = os.getenv('REDDIT_CLIENT_ID')
    reddit_client_secret: Optional[str] = os.getenv('REDDIT_CLIENT_SECRET')
    reddit_user_agent: str = os.getenv('REDDIT_USER_AGENT', 'SecretSpotsScraper/1.0')
    
    # Instagram settings
    instagram_username: Optional[str] = os.getenv('INSTAGRAM_USERNAME')
    instagram_password: Optional[str] = os.getenv('INSTAGRAM_PASSWORD')
    
    # Request settings
    request_timeout: int = int(os.getenv('REQUEST_TIMEOUT', '30'))
    max_retries: int = int(os.getenv('MAX_RETRIES', '3'))
    
    # Selenium settings
    headless_mode: bool = os.getenv('HEADLESS_MODE', 'true').lower() == 'true'
    webdriver_path: Optional[str] = os.getenv('WEBDRIVER_PATH')
    
    # Rate limiting
    min_delay: float = float(os.getenv('MIN_DELAY', '1.0'))
    max_delay: float = float(os.getenv('MAX_DELAY', '3.0'))
    
    # Database
    db_path: str = os.getenv('DB_PATH', '../hidden_spots.db')
    
    # Logging
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    log_file: Optional[str] = os.getenv('LOG_FILE')


# Singleton instance
config = ScraperConfig()
''')
        print(f"  ✅ Created config/scraper_config.py")
    
    # Create .env.example
    env_example = Path("../.env.example")
    if not env_example.exists():
        env_example.write_text('''# Reddit API credentials
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=SecretSpotsScraper/1.0

# Instagram credentials (optional)
INSTAGRAM_USERNAME=your_username_here
INSTAGRAM_PASSWORD=your_password_here

# Request settings
REQUEST_TIMEOUT=30
MAX_RETRIES=3

# Selenium settings
HEADLESS_MODE=true
WEBDRIVER_PATH=/usr/bin/chromedriver

# Rate limiting (seconds)
MIN_DELAY=1.0
MAX_DELAY=3.0

# Database
DB_PATH=../hidden_spots.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=../logs/scraper.log
''')
        print(f"  ✅ Created .env.example")
    
    print()


def main():
    """Run all critical fixes"""
    print("🚀 Applying critical fixes from official documentation review\n")
    
    # Change to scrapers directory
    os.chdir(Path(__file__).parent)
    
    # Apply fixes
    fix_beautifulsoup_parsers()
    fix_requests_timeouts()
    fix_response_validation()
    add_selenium_cleanup()
    create_config_file()
    
    print("✨ Critical fixes applied!")
    print("\nNext steps:")
    print("1. Review the changes with 'git diff'")
    print("2. Test the scrapers to ensure they still work")
    print("3. Copy .env.example to .env and add your credentials")
    print("4. Implement the remaining HIGH priority fixes from OFFICIAL_DOCS_GAP_ANALYSIS.md")


if __name__ == "__main__":
    main()