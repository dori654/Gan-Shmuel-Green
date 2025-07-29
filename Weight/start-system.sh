#!/bin/bash

# Gan Shmuel Weighing System - Complete System Startup
echo "🚀 Starting Gan Shmuel Weighing System..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating example file..."
    cp .env.example .env
    echo "📝 Please edit .env file with your database settings"
    exit 1
fi

# Build images
echo "🔨 Building Docker images..."
docker-compose build

# Start the system
echo "🎯 Starting the system..."
docker-compose up -d

# Wait for services to load
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "🔍 Checking service status..."
docker-compose ps

echo ""
echo "✅ System started successfully!"
echo ""
echo "📱 Frontend UI: http://localhost:8080"
echo "🔧 API Backend: http://localhost:5000"
echo "🗄️  MySQL Database: localhost:3306"
echo ""
echo "📋 Useful commands:"
echo "   docker-compose logs -f          # View logs"
echo "   docker-compose down             # Stop system"
echo "   docker-compose restart          # Restart system"
echo ""
echo "🎉 System ready for use!"
