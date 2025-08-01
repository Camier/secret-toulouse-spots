#!/usr/bin/env python3
"""
Get map performance insights from Mistral
"""

import subprocess

def get_map_insights(code_file, model="mistral-nemo:latest"):
    """Get insights on map performance optimization"""
    
    prompt = """You are reviewing map visualization code that needs to render 3000+ markers efficiently.

Challenge: Browser freezes when rendering all markers at once on Leaflet map.

Please analyze this code and provide specific solutions for:
1. Marker clustering strategies for better performance
2. Lazy loading and viewport-based rendering
3. Data structure optimizations for faster filtering
4. Progressive rendering techniques
5. Memory-efficient data formats

Focus on practical Leaflet.js optimizations and Python data preparation improvements.

Code to review:
"""
    
    with open(code_file, 'r') as f:
        code_content = f.read()
    
    full_prompt = prompt + "\n\n" + code_content + "\n\nProvide specific map performance improvements:"
    
    cmd = ["ollama", "run", model, full_prompt]
    
    print(f"🤖 Consulting {model} for map performance insights...")
    print("This may take a minute...\n")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    insights = get_map_insights("map_performance_code.py")
    
    with open("MISTRAL_MAP_INSIGHTS.md", "w") as f:
        f.write("# Mistral Nemo Insights on Map Performance\n\n")
        f.write("## Challenge: Rendering 3000+ Markers Efficiently\n\n")
        f.write("### Analysis Results:\n\n")
        f.write(insights)
    
    print("✅ Map performance insights saved to MISTRAL_MAP_INSIGHTS.md")