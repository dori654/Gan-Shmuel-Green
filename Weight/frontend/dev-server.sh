#!/bin/bash

# Gan Shmuel Weighing System - Development Server
echo "🔧 Starting development server for frontend..."
echo "📱 Frontend will be available at: http://localhost:8080"
echo "🔗 Make sure Flask backend is running on: http://localhost:5000"
echo "⏹️  To stop: Ctrl+C"
echo "$(printf '%*s' 50 | tr ' ' '-')"

# Start the server
python3 server.py
