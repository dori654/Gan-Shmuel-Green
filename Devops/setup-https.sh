#!/bin/bash

echo "?? Setting up HTTPS CI server with nginx..."

# Generate SSL certificate
if [ ! -f cert.pem ] || [ ! -f key.pem ]; then
    echo "?? Generating SSL certificate..."
    openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 -subj "/C=US/ST=State/L=City/O=Organization/CN=13.126.238.4"
    echo "? SSL certificate generated"
fi

# Stop existing containers
echo "?? Stopping existing containers..."
docker rm -f $(docker ps -aq) 2>/dev/null || true

# Start services with nginx
echo "?? Starting HTTPS CI server..."
docker-compose -f docker-compose-nginx.yml up -d

echo "? CI server running with HTTPS support!"
echo "?? HTTP:  http://13.126.238.4/trigger (redirects to HTTPS)"
echo "?? HTTPS: https://13.126.238.4/trigger"
echo ""
echo "?? Update your GitHub webhook to: https://13.126.238.4/trigger"
echo "??  Disable SSL verification in GitHub webhook settings (self-signed cert)"
