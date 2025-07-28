FROM python:3.13-slim
RUN apt update && apt install -y --no-install-recommends \
    apt-utils \
    curl \
    ca-certificates \
    git \
    && curl -fsSL https://get.docker.com | bash \
    && curl -L "https://github.com/docker/compose/releases/download/$(curl -s https://api.github.com/repos/docker/compose/releases/latest | jq -r .tag_name)/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN mkdir -p /app
COPY . /app
WORKDIR /app
EXPOSE 8080
CMD ["python", "./app/app.py"]