# Testing Guide

This document describes how to test the FastAPI webhook service.

## Running Automated Tests

### Using Make

```bash
make test
```

### Using pytest directly

```bash
# Install dependencies first
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_webhook.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## Manual Testing with curl

### 1. Start the Service

```bash
make up
# Wait a few seconds for service to start
```

### 2. Check Health

```bash
# Liveness probe
curl http://localhost:8000/health/live

# Readiness probe
curl http://localhost:8000/health/ready
```

### 3. Test Webhook Endpoint

#### Valid Request

```bash
# Set your secret
SECRET="mysecretkey"

# Create payload
BODY='{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'

# Compute signature
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

# Send request
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"

# Expected: {"status":"ok"}
```

#### Invalid Signature

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: invalid" \
  -d "$BODY"

# Expected: 401 {"detail":"invalid signature"}
```

#### Invalid Payload

```bash
# Missing required field
BODY='{"message_id":"m2","from":"+919876543210"}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"

# Expected: 422 validation error
```

#### Idempotency Test

```bash
# Send same message twice
BODY='{"message_id":"m3","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Test"}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

# First request
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"

# Second request (duplicate)
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"

# Both should return 200 {"status":"ok"}
```

### 4. Test Messages Endpoint

```bash
# Basic listing
curl http://localhost:8000/messages | jq .

# With pagination
curl "http://localhost:8000/messages?limit=10&offset=0" | jq .

# Filter by sender
curl "http://localhost:8000/messages?from=%2B919876543210" | jq .

# Filter by timestamp
curl "http://localhost:8000/messages?since=2025-01-15T09:00:00Z" | jq .

# Text search
curl "http://localhost:8000/messages?q=hello" | jq .

# Combined filters
curl "http://localhost:8000/messages?from=%2B919876543210&limit=5&q=test" | jq .
```

### 5. Test Stats Endpoint

```bash
curl http://localhost:8000/stats | jq .
```

### 6. Test Metrics Endpoint

```bash
curl http://localhost:8000/metrics
```

## Using the Test Script

A convenience script is provided for quick testing:

```bash
chmod +x test_api.sh
./test_api.sh
```

## Viewing Logs

```bash
# Follow logs
make logs

# View specific number of lines
docker compose logs --tail=100 api

# View logs with timestamps
docker compose logs -t api
```

## Testing Scenarios

### Scenario 1: Basic Message Flow

1. Send a message via webhook
2. Verify it appears in /messages
3. Check stats are updated
4. Verify metrics show the request

### Scenario 2: Signature Verification

1. Send message with valid signature → 200
2. Send message with invalid signature → 401
3. Send message without signature → 401
4. Verify metrics show invalid_signature count

### Scenario 3: Idempotency

1. Send message with message_id "test1" → 200
2. Send same message again → 200 (no error)
3. Verify only one message in database
4. Check metrics show duplicate count

### Scenario 4: Validation

1. Send message with invalid E.164 format → 422
2. Send message with invalid timestamp → 422
3. Send message with text > 4096 chars → 422
4. Verify metrics show validation_error count

### Scenario 5: Pagination

1. Insert 25 messages
2. Get first page (limit=10, offset=0)
3. Get second page (limit=10, offset=10)
4. Verify total count is consistent
5. Verify ordering is by ts ASC, message_id ASC

### Scenario 6: Filtering

1. Insert messages from multiple senders
2. Filter by specific sender
3. Verify only that sender's messages returned
4. Test since filter with various timestamps
5. Test text search with partial matches

## Performance Testing

### Load Testing with Apache Bench

```bash
# Install ab (Apache Bench)
# Ubuntu: apt-get install apache2-utils
# Mac: brew install httpd

# Test health endpoint
ab -n 1000 -c 10 http://localhost:8000/health/live

# Test messages endpoint
ab -n 1000 -c 10 http://localhost:8000/messages
```

### Load Testing Webhook

Create a script to send multiple webhook requests:

```bash
#!/bin/bash
SECRET="mysecretkey"

for i in {1..100}; do
  BODY="{\"message_id\":\"load_$i\",\"from\":\"+919876543210\",\"to\":\"+14155550100\",\"ts\":\"2025-01-15T10:00:00Z\",\"text\":\"Load test $i\"}"
  SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)
  
  curl -s -X POST http://localhost:8000/webhook \
    -H "Content-Type: application/json" \
    -H "X-Signature: $SIGNATURE" \
    -d "$BODY" &
done

wait
echo "Load test complete"
```

## Troubleshooting Tests

### Tests fail with "WEBHOOK_SECRET not set"

Ensure the environment variable is set:
```bash
export WEBHOOK_SECRET=test_secret_key
pytest tests/ -v
```

### Tests fail with database errors

Check that the data directory is writable:
```bash
mkdir -p data
chmod 777 data
```

### Docker tests fail

Ensure Docker is running and you have permissions:
```bash
docker ps
make down
make up
```

### Signature computation fails

Ensure you're using the raw body bytes:
```bash
# Correct
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

# Incorrect (adds newline)
SIGNATURE=$(echo "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)
```
