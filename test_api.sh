#!/bin/bash

# Test script for FastAPI webhook service
# Usage: ./test_api.sh

set -e

BASE_URL="http://localhost:8000"
SECRET="mysecretkey"

echo "Testing FastAPI Webhook Service..."
echo ""

# Test health endpoints
echo "1. Testing health endpoints..."
curl -s "$BASE_URL/health/live" | jq .
curl -s "$BASE_URL/health/ready" | jq .
echo ""

# Test webhook with valid signature
echo "2. Testing webhook with valid signature..."
BODY='{"message_id":"test1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello World"}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -s -X POST "$BASE_URL/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY" | jq .
echo ""

# Test webhook idempotency
echo "3. Testing webhook idempotency (duplicate message_id)..."
curl -s -X POST "$BASE_URL/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY" | jq .
echo ""

# Test webhook with invalid signature
echo "4. Testing webhook with invalid signature..."
curl -s -X POST "$BASE_URL/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Signature: invalid" \
  -d "$BODY" | jq .
echo ""

# Test messages endpoint
echo "5. Testing messages endpoint..."
curl -s "$BASE_URL/messages?limit=10" | jq .
echo ""

# Test stats endpoint
echo "6. Testing stats endpoint..."
curl -s "$BASE_URL/stats" | jq .
echo ""

# Test metrics endpoint
echo "7. Testing metrics endpoint..."
curl -s "$BASE_URL/metrics" | head -20
echo ""

echo "All tests completed!"
