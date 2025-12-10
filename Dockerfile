FROM python:3.10-slim

# Set application version (will be used by frontend)
ENV APP_VERSION="1.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install docker-compose v2
RUN curl -SL https://github.com/docker/compose/releases/download/v2.20.3/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for yml files
RUN mkdir -p /app/data/local /app/data/fnOS /app/data/QNAP /app/data/Synology /app/data/TrueNAS /app/data/UgreenNew /app/data/Ugreen /app/data/ZSpace /app/data/ZimaOS

# Set permissions
RUN chmod -R 777 /app/data

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]