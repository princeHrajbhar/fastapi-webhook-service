# API Documentation

Complete API reference for the FastAPI Webhook Service.

## Base URL

```
http://localhost:8000
```

## Authentication

All webhook requests require HMAC-SHA256 signature verification via the `X-Signature` header.

### Signature Computation

```python
import hmac
import hashlib

def compute_signature(body_bytes: bytes, secret: str) -> str:
    return hmac.new(
        secret.encode(),
        body_bytes,
        hashlib.sha256
    ).hexdigest()
```

```bash
# Using openssl
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)
```

## Endpoints

### POST /webhook

Ingest inbound WhatsApp-like messages with signature verification and idempotency.

#### Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Content-Type` | Yes | Must be `application/json` |
| `X-Signature` | Yes | HMAC-SHA256 hex signature of raw body |

#### Request Body

```json
{
  "message_id": "string",
  "from": "string",
  "to": "string",
  "ts": "string",
  "text": "string"
}
```

**Field Validation:**

- `message_id`: Non-empty string, used for idempotency
- `from`: E.164 format (+ followed by digits only)
- `to`: E.164 format (+ followed by digits only)
- `ts`: ISO-8601 UTC timestamp with Z suffix (e.g., "2025-01-15T10:00:00Z")
- `text`: Optional, max 4096 characters

#### Response

**Success (200 OK):**
```json
{
  "status": "ok"
}
```

**Invalid Signature (401 Unauthorized):**
```json
{
  "detail": "invalid signature"
}
```

**Validation Error (422 Unprocessable Entity):**
```json
{
  "detail": [
    {
      "loc": ["body", "from"],
      "msg": "must be E.164 format: + followed by digits",
      "type": "value_error"
    }
  ]
}
```

#### Idempotency

- Duplicate `message_id` values are handled gracefully
- Returns 200 OK with same response body
- Does NOT insert duplicate row
- Metrics track duplicates separately

#### Examples

**Valid Request:**
```bash
BODY='{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "mysecretkey" | cut -d' ' -f2)

curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
```

**Invalid E.164 Format:**
```bash
BODY='{"message_id":"m2","from":"invalid","to":"+14155550100","ts":"2025-01-15T10:00:00Z"}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "mysecretkey" | cut -d' ' -f2)

curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
# Returns 422
```

---

### GET /messages

Retrieve paginated and filtered list of messages.

#### Query Parameters

| Parameter | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| `limit` | integer | No | 50 | 1-100 | Results per page |
| `offset` | integer | No | 0 | >= 0 | Pagination offset |
| `from` | string | No | - | - | Filter by sender (exact match) |
| `since` | string | No | - | ISO-8601 UTC | Filter messages with ts >= since |
| `q` | string | No | - | - | Case-insensitive text search |

#### Response

**Success (200 OK):**
```json
{
  "data": [
    {
      "message_id": "m1",
      "from": "+919876543210",
      "to": "+14155550100",
      "ts": "2025-01-15T10:00:00Z",
      "text": "Hello"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

**Fields:**

- `data`: Array of message objects
- `total`: Total count of messages matching filters (ignoring limit/offset)
- `limit`: Applied limit value
- `offset`: Applied offset value

#### Ordering

Results are always ordered by:
1. `ts` ASC (timestamp ascending)
2. `message_id` ASC (alphabetical)

This ensures deterministic pagination.

#### Examples

**Basic Listing:**
```bash
curl http://localhost:8000/messages
```

**Pagination:**
```bash
curl "http://localhost:8000/messages?limit=10&offset=20"
```

**Filter by Sender:**
```bash
curl "http://localhost:8000/messages?from=%2B919876543210"
```

**Filter by Timestamp:**
```bash
curl "http://localhost:8000/messages?since=2025-01-15T09:00:00Z"
```

**Text Search:**
```bash
curl "http://localhost:8000/messages?q=hello"
```

**Combined Filters:**
```bash
curl "http://localhost:8000/messages?from=%2B919876543210&since=2025-01-15T09:00:00Z&q=test&limit=20"
```

---

### GET /stats

Retrieve message statistics and analytics.

#### Response

**Success (200 OK):**
```json
{
  "total_messages": 123,
  "senders_count": 10,
  "messages_per_sender": [
    {
      "from": "+919876543210",
      "count": 50
    },
    {
      "from": "+918888888888",
      "count": 30
    }
  ],
  "first_message_ts": "2025-01-10T09:00:00Z",
  "last_message_ts": "2025-01-15T10:00:00Z"
}
```

**Fields:**

- `total_messages`: Total number of messages in database
- `senders_count`: Number of unique senders
- `messages_per_sender`: Top 10 senders by message count (sorted DESC)
- `first_message_ts`: Timestamp of earliest message (null if no messages)
- `last_message_ts`: Timestamp of latest message (null if no messages)

#### Examples

```bash
curl http://localhost:8000/stats | jq .
```

---

### GET /health/live

Liveness probe for Kubernetes/container orchestration.

#### Response

**Always returns 200 OK when app is running:**
```json
{
  "status": "ok"
}
```

#### Examples

```bash
curl http://localhost:8000/health/live
```

---

### GET /health/ready

Readiness probe for Kubernetes/container orchestration.

#### Response

**Ready (200 OK):**
```json
{
  "status": "ready"
}
```

**Not Ready (503 Service Unavailable):**
```json
{
  "status": "not ready",
  "reason": "WEBHOOK_SECRET not set"
}
```

or

```json
{
  "status": "not ready",
  "reason": "database not ready"
}
```

#### Readiness Checks

Service is ready when:
1. `WEBHOOK_SECRET` environment variable is set
2. Database is accessible and schema exists

#### Examples

```bash
curl http://localhost:8000/health/ready
```

---

### GET /metrics

Prometheus metrics endpoint in text exposition format.

#### Response

**Success (200 OK):**
```
# HELP http_requests_total Total HTTP requests by path and status
# TYPE http_requests_total counter
http_requests_total{path="/webhook",status="200"} 150
http_requests_total{path="/messages",status="200"} 45
http_requests_total{path="/stats",status="200"} 12

# HELP webhook_requests_total Total webhook requests by result
# TYPE webhook_requests_total counter
webhook_requests_total{result="created"} 100
webhook_requests_total{result="duplicate"} 30
webhook_requests_total{result="invalid_signature"} 15
webhook_requests_total{result="validation_error"} 5

# HELP request_latency_ms Request latency in milliseconds
# TYPE request_latency_ms summary
request_latency_ms_count 207
request_latency_ms_sum 3145.67
request_latency_ms{quantile="0.5"} 12.34
request_latency_ms{quantile="0.9"} 45.67
request_latency_ms{quantile="0.99"} 123.45
```

#### Metrics Included

**http_requests_total**
- Type: Counter
- Labels: `path`, `status`
- Description: Total HTTP requests by endpoint and status code

**webhook_requests_total**
- Type: Counter
- Labels: `result`
- Values: `created`, `duplicate`, `invalid_signature`, `validation_error`
- Description: Webhook request outcomes

**request_latency_ms**
- Type: Summary
- Quantiles: 0.5 (median), 0.9, 0.99
- Description: Request latency in milliseconds

#### Examples

```bash
curl http://localhost:8000/metrics
```

**Scrape with Prometheus:**
```yaml
scrape_configs:
  - job_name: 'fastapi-webhook'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

---

## Error Responses

### 401 Unauthorized

Invalid or missing signature.

```json
{
  "detail": "invalid signature"
}
```

### 422 Unprocessable Entity

Validation error in request payload.

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "error message",
      "type": "error_type"
    }
  ]
}
```

### 503 Service Unavailable

Service not ready (health check failure).

```json
{
  "status": "not ready",
  "reason": "reason description"
}
```

---

## Rate Limiting

Currently not implemented. Consider adding rate limiting in production:

- Per-IP rate limiting
- Per-sender rate limiting
- Global rate limiting

---

## Logging

All requests are logged in structured JSON format:

```json
{
  "ts": "2025-01-15T10:00:00Z",
  "level": "INFO",
  "message": "POST /webhook 200",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/webhook",
  "status": 200,
  "latency_ms": 12.34,
  "message_id": "m1",
  "dup": false,
  "result": "created"
}
```

---

## Best Practices

### Signature Verification

- Always use raw body bytes for signature computation
- Use constant-time comparison to prevent timing attacks
- Rotate secrets regularly

### Idempotency

- Use unique `message_id` for each message
- Retry failed requests with same `message_id`
- Handle 200 responses as success (even for duplicates)

### Pagination

- Use consistent `limit` and `offset` values
- Don't rely on specific page contents (data may change)
- Use `total` field to calculate total pages

### Error Handling

- Check status codes before parsing response
- Log all 4xx and 5xx responses
- Implement exponential backoff for retries

### Performance

- Use connection pooling for multiple requests
- Implement client-side caching for stats
- Monitor metrics endpoint for performance insights
