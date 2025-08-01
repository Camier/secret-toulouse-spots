#!/usr/bin/env python3
"""
Get Instagram scraper insights from Mistral Nemo
"""

import subprocess

def get_instagram_insights(code_file, model="mistral-nemo:latest"):
    """Get insights from Mistral on Instagram scraping challenges"""
    
    prompt = """You are reviewing Instagram scraping code for a project that finds secret outdoor spots.

Challenge: Instagram has no official API for public content, making scraping difficult.

Please analyze this Instagram scraper code and provide specific improvements for:
1. Anti-bot detection avoidance strategies
2. Rate limiting and human-like behavior patterns  
3. Alternative data extraction methods when Instagram blocks access
4. Handling dynamic content loading (infinite scroll)
5. Extracting geolocation from posts without explicit coordinates

Focus on practical, implementable solutions that respect rate limits and avoid detection.

Code to review:
"""
    
    with open(code_file, 'r') as f:
        code_content = f.read()
    
    full_prompt = prompt + "\n\n" + code_content + "\n\nProvide specific Instagram scraping improvements:"
    
    cmd = ["ollama", "run", model, full_prompt]
    
    print(f"🤖 Consulting {model} for Instagram scraping insights...")
    print("This may take a minute...\n")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    insights = get_instagram_insights("critical_instagram_code.py")
    
    with open("MISTRAL_INSTAGRAM_INSIGHTS.md", "w") as f:
        f.write("# Mistral Nemo Insights on Instagram Scraping\n\n")
        f.write("## Challenge: No Official API for Public Content\n\n")
        f.write("### Analysis Results:\n\n")
        f.write(insights)
    
    print("✅ Instagram scraping insights saved to MISTRAL_INSTAGRAM_INSIGHTS.md")