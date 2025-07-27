#!/bin/bash

# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 -subj "/C=US/ST=State/L=City/O=Organization/CN=13.126.238.4"

docker rm -f $(docker ps -aq) 2>/dev/null || true
docker build -t ci .
docker run -d -it --name ci_container \
  -p 8080:8080 \
  -v $(pwd)/cert.pem:/app/cert.pem \
  -v $(pwd)/key.pem:/app/key.pem \
  ci
