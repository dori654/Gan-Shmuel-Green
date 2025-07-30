# ----------- Stage 1: Builder (installs dependencies into /install) ----------
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt
# ----------- Stage 2: Runtime (tiny image, only what’s needed) ---------------
FROM python:3.11-alpine
WORKDIR /app
RUN apk add --no-cache libstdc++ mariadb-connector-c
# Copy Python packages from builder stage to /usr/local in runtime
COPY --from=builder /install /usr/local
# Copy your application code (app folder) into the image
COPY app ./app
EXPOSE 5000
ENTRYPOINT [“python”, “-m”, “app.main”]