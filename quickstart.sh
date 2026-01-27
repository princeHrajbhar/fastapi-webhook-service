#!/bin/bash

# Quick start script for FastAPI Webhook Service
# This script sets up and starts the service with default configuration

set -e

echo "=========================================="
echo "FastAPI Webhook Service - Quick Start"
echo "=========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo "Error: docker-compose is not installed. Please install it and try again."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file with default configuration..."
    cat > .env << EOF
WEBHOOK_SECRET=mysecretkey
DATABASE_URL=sqlite:////data/app.db
LOG_LEVEL=INFO
EOF
    echo "✓ .env file created"
else
    echo "✓ .env file already exists"
fi

# Create data directory
mkdir -p data
echo "✓ Data directory created"

# Stop any existing containers
echo ""
echo "Stopping any existing containers..."
docker compose down -v 2>/dev/null || true

# Build and start the service
echo ""
echo "Building and starting the service..."
docker compose up -d --build

# Wait for service to be ready
echo ""
echo "Waiting for service to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health/ready > /dev/null 2>&1; then
        echo "✓ Service is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Error: Service did not become ready in time"
        echo "Check logs with: docker compose logs api"
        exit 1
    fi
    sleep 1
    echo -n "."
done

echo ""
echo ""
echo "=========================================="
echo "Service is running!"
echo "=========================================="
echo ""
echo "API Endpoints:"
echo "  - Health (live):  http://localhost:8000/health/live"
echo "  - Health (ready): http://localhost:8000/health/ready"
echo "  - Webhook:        http://localhost:8000/webhook"
echo "  - Messages:       http://localhost:8000/messages"
echo "  - Stats:          http://localhost:8000/stats"
echo "  - Metrics:        http://localhost:8000/metrics"
echo ""
echo "Useful commands:"
echo "  - View logs:      make logs"
echo "  - Stop service:   make down"
echo "  - Run tests:      ./test_api.sh"
echo ""
echo "Example webhook request:"
echo '  BODY='"'"'{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'"'"
echo '  SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "mysecretkey" | cut -d'"'"' '"'"' -f2)'
echo '  curl -X POST http://localhost:8000/webhook \'
echo '    -H "Content-Type: application/json" \'
echo '    -H "X-Signature: $SIGNATURE" \'
echo '    -d "$BODY"'
echo ""
