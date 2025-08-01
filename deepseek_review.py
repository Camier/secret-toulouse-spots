#!/usr/bin/env python3
"""
Get code enhancement insights from DeepSeek Coder
"""

import subprocess
import json

def get_deepseek_insights(code_file, model="mistral-nemo:latest"):
    """Get insights from DeepSeek Coder on critical code sections"""
    
    prompt = """You are reviewing critical code sections from a project that discovers and maps secret/hidden outdoor spots around Toulouse, France.

Project Goal: Find rare, abandoned, or difficult-to-access natural spots (waterfalls, caves, ruins, swimming holes) by scraping multiple sources and filtering for relevance.

Please analyze the following code sections and provide specific enhancement suggestions focused on:
1. Performance optimizations for handling 3000+ spots
2. Algorithm improvements for better secret spot detection
3. Data quality enhancements
4. Scalability considerations
5. Code robustness and error handling

Code to review:
"""
    
    # Read the code file
    with open(code_file, 'r') as f:
        code_content = f.read()
    
    full_prompt = prompt + "\n\n" + code_content + "\n\nProvide specific, actionable improvements:"
    
    # Call ollama with the model
    cmd = [
        "ollama", "run", model,
        full_prompt
    ]
    
    print(f"🤖 Consulting {model} for code insights...")
    print("This may take a minute...\n")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Model took too long to respond"
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    # Get insights on the critical code
    insights = get_deepseek_insights("critical_code_for_deepseek.py")
    
    # Save the insights
    with open("DEEPSEEK_INSIGHTS.md", "w") as f:
        f.write("# DeepSeek Coder Insights on Critical Code Sections\n\n")
        f.write("## Model: mistral-nemo:latest (optimized for code analysis)\n\n")
        f.write("### Analysis Results:\n\n")
        f.write(insights)
    
    print("✅ DeepSeek insights saved to DEEPSEEK_INSIGHTS.md")