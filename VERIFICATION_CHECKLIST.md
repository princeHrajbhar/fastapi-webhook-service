# Verification Checklist

Use this checklist to verify the implementation matches the specification exactly.

## Core Requirements

- [x] Language: Python 3.11+
- [x] Framework: FastAPI
- [x] Database: SQLite only
- [x] Async DB access: aiosqlite
- [x] Validation: Pydantic
- [x] Config: Environment variables only
- [x] No external services (Redis, Postgres, Kafka)

## Environment Variables

- [x] `DATABASE_URL` - SQLite path (default: sqlite:////data/app.db)
- [x] `WEBHOOK_SECRET` - Required, non-empty string
- [x] `LOG_LEVEL` - Default INFO
- [x] App fails startup if WEBHOOK_SECRET missing
- [x] /health/ready returns 503 if WEBHOOK_SECRET missing

## Data Model

- [x] Table name: `messages`
- [x] Fields: message_id (PK), from_msisdn, to_msisdn, ts, text, created_at
- [x] Created on startup if not exists
- [x] Primary key on message_id
- [x] Idempotency via DB constraint

## POST /webhook

### Request
- [x] Header: Content-Type: application/json
- [x] Header: X-Signature (HMAC-SHA256)
- [x] Body fields: message_id, from, to, ts, text

### Signature Validation
- [x] Uses raw request body bytes
- [x] HMAC-SHA256 with WEBHOOK_SECRET
- [x] Hex output
- [x] Constant-time comparison
- [x] Invalid signature: 401 with {"detail": "invalid signature"}
- [x] No DB insert on invalid signature
- [x] Logs error on invalid signature
- [x] Metrics record invalid_signature

### Payload Validation
- [x] message_id: non-empty string
- [x] from/to: E.164 format (+ then digits)
- [x] ts: ISO-8601 UTC with Z
- [x] text: optional, max 4096 chars
- [x] Invalid payload: 422 (Pydantic default)
- [x] No DB insert on validation error
- [x] Metrics record validation_error

### Idempotency
- [x] First call: insert row, return {"status": "ok"}
- [x] Duplicate call: no insert, return 200 {"status": "ok"}
- [x] No stack trace on duplicate
- [x] Metrics record duplicate

## GET /messages

### Query Parameters
- [x] limit: default 50, min 1, max 100
- [x] offset: default 0, min 0
- [x] from: exact match on sender
- [x] since: ISO-8601 UTC, ts >= since
- [x] q: case-insensitive substring on text

### Ordering
- [x] ORDER BY ts ASC, message_id ASC

### Response Shape
- [x] data: array of messages
- [x] total: total matching rows (ignoring limit/offset)
- [x] limit: applied limit
- [x] offset: applied offset
- [x] Message fields: message_id, from, to, ts, text

## GET /stats

### Response Fields
- [x] total_messages: count of all messages
- [x] senders_count: distinct sender count
- [x] messages_per_sender: top 10, sorted by count DESC
- [x] first_message_ts: earliest ts (null if no messages)
- [x] last_message_ts: latest ts (null if no messages)

## Health Endpoints

### GET /health/live
- [x] Always returns 200 when app running

### GET /health/ready
- [x] Returns 200 if DB reachable and WEBHOOK_SECRET set
- [x] Returns 503 otherwise

## GET /metrics

- [x] Prometheus text exposition format
- [x] Returns HTTP 200
- [x] http_requests_total{path,status}
- [x] webhook_requests_total{result}
- [x] Results: created, duplicate, invalid_signature, validation_error
- [x] Request latency metrics

## Structured Logging

- [x] One JSON object per line
- [x] Fields: ts (ISO-8601 UTC), level, request_id, method, path, status, latency_ms
- [x] Webhook logs: message_id, dup, result
- [x] Valid JSON (pipeable to jq)

## Containerization

- [x] Multi-stage Dockerfile
- [x] Small runtime image
- [x] SQLite DB at /data/app.db
- [x] Docker Compose with service name: api
- [x] Exposed on http://localhost:8000
- [x] Volume for /data

## Repository Structure

- [x] /app/main.py
- [x] /app/models.py
- [x] /app/storage.py
- [x] /app/logging_utils.py
- [x] /app/metrics.py
- [x] /app/config.py
- [x] /tests/test_webhook.py
- [x] /tests/test_messages.py
- [x] /tests/test_stats.py
- [x] Dockerfile
- [x] docker-compose.yml
- [x] Makefile
- [x] README.md

## Makefile Targets

- [x] make up: docker compose up -d --build
- [x] make down: docker compose down -v
- [x] make logs: docker compose logs -f api
- [x] make test: run tests

## README Requirements

- [x] How to run
- [x] How to hit endpoints
- [x] Design decisions: HMAC verification
- [x] Design decisions: Pagination logic
- [x] Design decisions: Stats computation
- [x] Setup used: VSCode + Copilot + ChatGPT

## HTTP Status Codes

- [x] 200: Success (webhook, messages, stats, health)
- [x] 401: Invalid signature
- [x] 422: Validation error
- [x] 503: Service not ready

## Field Names

- [x] Webhook request: message_id, from, to, ts, text
- [x] Webhook response: status
- [x] Messages response: data, total, limit, offset
- [x] Message object: message_id, from, to, ts, text
- [x] Stats response: total_messages, senders_count, messages_per_sender, first_message_ts, last_message_ts
- [x] Sender count: from, count

## Response Shapes

- [x] Webhook: {"status": "ok"}
- [x] Invalid signature: {"detail": "invalid signature"}
- [x] Messages: {data: [], total: N, limit: N, offset: N}
- [x] Stats: {total_messages, senders_count, messages_per_sender: [], first_message_ts, last_message_ts}

## Testing

Run these tests to verify:

```bash
# 1. Start service
make up

# 2. Test health endpoints
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready

# 3. Test webhook with valid signature
BODY='{"message_id":"v1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Test"}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "mysecretkey" | cut -d' ' -f2)
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
# Expected: {"status":"ok"}

# 4. Test webhook with invalid signature
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: invalid" \
  -d "$BODY"
# Expected: 401 {"detail":"invalid signature"}

# 5. Test idempotency (send same message twice)
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
# Expected: 200 {"status":"ok"}

# 6. Test messages endpoint
curl http://localhost:8000/messages
# Expected: {data: [...], total: N, limit: 50, offset: 0}

# 7. Test stats endpoint
curl http://localhost:8000/stats
# Expected: {total_messages: N, senders_count: N, messages_per_sender: [...], ...}

# 8. Test metrics endpoint
curl http://localhost:8000/metrics
# Expected: Prometheus text format

# 9. Run automated tests
make test

# 10. Check logs are JSON
make logs | head -20
# Expected: Valid JSON lines
```

## Automated Evaluation

The implementation should pass strict curl-based evaluation that checks:

- [x] HTTP status codes match exactly
- [x] JSON response shapes match exactly
- [x] Field names match exactly
- [x] Ordering is correct (ts ASC, message_id ASC)
- [x] Idempotency works correctly
- [x] Signature verification works correctly
- [x] Validation errors return 422
- [x] Logging is structured JSON
- [x] Metrics are in Prometheus format

## Final Verification

```bash
# Run complete test suite
./test_api.sh

# Verify all tests pass
make test

# Check Docker build
docker build -t test-build .

# Verify structure
ls -la app/
ls -la tests/

# Check documentation
cat README.md | grep "Setup Used"
```

All items checked! ✅
