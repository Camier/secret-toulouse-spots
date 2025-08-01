#!/usr/bin/env python3
"""
Submit critical code parts to Ollama for review
"""

import subprocess
import json
from pathlib import Path

def get_ollama_review(code_snippet, filename, focus_areas):
    """Get code review from Ollama"""
    prompt = f"""Review this Python code from {filename}.
Focus on: {', '.join(focus_areas)}
Be concise with specific improvements.

```python
{code_snippet}
```
"""
    
    try:
        # Use a smaller model
        result = subprocess.run(
            ["ollama", "run", "codellama:7b", prompt],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def extract_critical_parts():
    """Extract critical code sections for review"""
    critical_sections = {
        "Base Scraper - Error Handling": {
            "file": "scrapers/base_scraper.py",
            "lines": (47, 95),  # save_spot method
            "focus": ["SQL injection", "Error handling", "Database connections"]
        },
        "Reddit Scraper - Authentication": {
            "file": "scrapers/unified_reddit_scraper.py", 
            "lines": (100, 113),  # _setup_praw_client
            "focus": ["Authentication security", "Error handling", "API key exposure"]
        },
        "Selenium Driver Management": {
            "file": "scrapers/forum_scraper.py",
            "lines": (528, 541),  # __enter__ and __exit__
            "focus": ["Resource cleanup", "Memory leaks", "Exception handling"]
        },
        "Coordinate Extraction": {
            "file": "scrapers/base_scraper.py",
            "lines": (103, 116),  # extract_coordinates
            "focus": ["Regex safety", "Input validation", "Performance"]
        }
    }
    
    results = {}
    for section_name, info in critical_sections.items():
        try:
            # Read the specific lines
            with open(info["file"], 'r') as f:
                lines = f.readlines()
                start, end = info["lines"]
                code_snippet = ''.join(lines[start-1:end])
                
            print(f"\n🔍 Reviewing: {section_name}")
            review = get_ollama_review(code_snippet, info["file"], info["focus"])
            results[section_name] = review
            print(review[:500] + "..." if len(review) > 500 else review)
            
        except Exception as e:
            results[section_name] = f"Error reading code: {str(e)}"
    
    return results

def main():
    print("🤖 Submitting critical code sections to Ollama for review...\n")
    
    # Check if Ollama is available
    try:
        subprocess.run(["ollama", "--version"], capture_output=True, check=True)
    except:
        print("❌ Ollama not found. Please install Ollama first.")
        return
    
    # Get reviews
    reviews = extract_critical_parts()
    
    # Save results
    output_file = Path("OLLAMA_CODE_REVIEW.md")
    with open(output_file, 'w') as f:
        f.write("# Ollama Code Review Results\n\n")
        f.write("## Summary\n")
        f.write("Critical code sections reviewed by local Ollama model (codellama:7b)\n\n")
        
        for section, review in reviews.items():
            f.write(f"### {section}\n")
            f.write(f"{review}\n\n")
            f.write("---\n\n")
    
    print(f"\n✅ Review complete! Results saved to {output_file}")

if __name__ == "__main__":
    main()