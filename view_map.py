#!/usr/bin/env python3
"""Simple server to view the secret spots map"""

import http.server
import os
import socketserver
import webbrowser

PORT = 8888

os.chdir(os.path.dirname(os.path.abspath(__file__)))

Handler = http.server.SimpleHTTPRequestHandler

print(f"🗺️  Secret Toulouse Spots Map Server")
print(f"📍 Server starting on port {PORT}...")
print(f"\n✨ Open your browser to: http://localhost:{PORT}/enhanced-map.html")
print(f"\nPress Ctrl+C to stop the server\n")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    webbrowser.open(f"http://localhost:{PORT}/enhanced-map.html")
    httpd.serve_forever()
