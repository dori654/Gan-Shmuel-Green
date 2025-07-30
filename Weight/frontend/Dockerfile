FROM python:3.10-slim

# Set working directory
WORKDIR /usr/src/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy frontend files
COPY . .

# Make server executable
RUN chmod +x server.py

# Expose port
EXPOSE 8083

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8083/ || exit 1

# Start the frontend server
CMD ["python3", "server.py"]