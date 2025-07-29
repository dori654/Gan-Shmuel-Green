#!/usr/bin/env python3
"""
Simple HTTP server to serve the Hebrew UI for Gan Shmuel weighing system
"""

import http.server
import socketserver
import os
import sys

# Change to the frontend directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

PORT = 8080

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to allow communication with Flask backend
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    try:
        with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
            print(f"🚀 Gan Shmuel Weighing System - Frontend Server")
            print(f"📱 Frontend available at: http://localhost:{PORT}")
            print(f"🔗 Make sure Flask backend is running on http://localhost:5000")
            print(f"⏹️  To stop: Ctrl+C")
            print("-" * 50)
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)
