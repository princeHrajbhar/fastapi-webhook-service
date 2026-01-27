# FastAPI Webhook Service

A production-grade FastAPI service for ingesting and managing WhatsApp-like webhook messages with SQLite storage, HMAC signature verification, and Prometheus metrics.

## Features

- **Webhook Ingestion**: POST /webhook with HMAC-SHA256 signature verification
- **Message Listing**: GET /messages with pagination and filtering
- **Statistics**: GET /stats with sender analytics
- **Health Checks**: Liveness and readiness probes
- **Metrics**: Prometheus-compatible metrics endpoint
- **Structured Logging**: JSON logs for easy parsing
- **Idempotency**: Duplicate message handling via DB constraints

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Make (optional, for convenience commands)

### Running the Service

1. **Set environment variables** (optional, defaults provided):
   ```bash
   export WEBHOOK_SECRET=mysecretkey
   export LOG_LEVEL=INFO
   ```

2. **Start the service**:
   ```bash
   make up
   # or
   docker compose up -d --build
   ```

3. **View logs**:
   ```bash
   make logs
   # or
   docker compose logs -f api
   ```

4. **Stop the service**:
   ```bash
   make down
   # or
   docker compose down -v
   ```

## API Endpoints

### POST /webhook

Ingest inbound messages with signature verification.

**Request**:
```bash
# Compute signature
BODY='{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "mysecretkey" | cut -d' ' -f2)

curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
```

**Response**:
```json
{"status": "ok"}
```

**Status Codes**:
- `200`: Success (created or duplicate)
- `401`: Invalid signature
- `422`: Validation error

### GET /messages

List messages with pagination and filtering.

**Query Parameters**:
- `limit` (int): Results per page (default: 50, min: 1, max: 100)
- `offset` (int): Pagination offset (default: 0)
- `from` (string): Filter by sender (exact match)
- `since` (ISO-8601): Filter by timestamp (>=)
- `q` (string): Search text (case-insensitive substring)

**Examples**:
```bash
# Basic listing
curl http://localhost:8000/messages

# Pagination
curl http://localhost:8000/messages?limit=10&offset=20

# Filter by sender
curl http://localhost:8000/messages?from=%2B919876543210

# Filter by timestamp
curl "http://localhost:8000/messages?since=2025-01-15T09:00:00Z"

# Text search
curl "http://localhost:8000/messages?q=hello"
```

**Response**:
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

### GET /stats

Get message statistics and analytics.

**Example**:
```bash
curl http://localhost:8000/stats
```

**Response**:
```json
{
  "total_messages": 123,
  "senders_count": 10,
  "messages_per_sender": [
    {"from": "+919876543210", "count": 50},
    {"from": "+918888888888", "count": 30}
  ],
  "first_message_ts": "2025-01-10T09:00:00Z",
  "last_message_ts": "2025-01-15T10:00:00Z"
}
```

### GET /health/live

Liveness probe - always returns 200 when app is running.

```bash
curl http://localhost:8000/health/live
```

### GET /health/ready

Readiness probe - returns 200 only when fully ready (DB accessible, WEBHOOK_SECRET set).

```bash
curl http://localhost:8000/health/ready
```

**Status Codes**:
- `200`: Service is ready
- `503`: Service not ready (missing config or DB issue)

### GET /metrics

Prometheus metrics in text exposition format.

```bash
curl http://localhost:8000/metrics
```

**Metrics Included**:
- `http_requests_total{path,status}`: Total HTTP requests by path and status
- `webhook_requests_total{result}`: Webhook outcomes (created, duplicate, invalid_signature, validation_error)
- `request_latency_ms`: Request latency summary with quantiles

## Configuration

All configuration is via environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | `sqlite:////data/app.db` | SQLite database path |
| `WEBHOOK_SECRET` | **Yes** | - | HMAC secret for signature verification |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

**Important**: The service will fail startup if `WEBHOOK_SECRET` is not set.

## Development

### Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
make test
# or
pytest tests/ -v
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=sqlite:///./data/app.db
export WEBHOOK_SECRET=mysecretkey
export LOG_LEVEL=DEBUG

# Run locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Design Decisions

### HMAC Verification Approach

- **Raw body bytes**: Signature is computed on raw request body bytes before JSON parsing
- **Constant-time comparison**: Uses `hmac.compare_digest()` to prevent timing attacks
- **Early validation**: Signature checked before payload parsing to reject invalid requests quickly

### Pagination Logic

- **Offset-based pagination**: Simple and predictable for API consumers
- **Consistent ordering**: Always `ORDER BY ts ASC, message_id ASC` for deterministic results
- **Total count**: Separate query to get total matching records (ignoring limit/offset)
- **Validation**: Enforced limits (1-100) to prevent resource exhaustion

### Stats Computation

- **Top 10 senders**: Limited to prevent large responses, sorted by count DESC
- **Null timestamps**: When no messages exist, timestamps are null (not empty strings)
- **Single query optimization**: Uses aggregate functions for efficient computation
- **Distinct senders**: Uses `COUNT(DISTINCT from_msisdn)` for accurate sender count

### Idempotency

- **Database-level enforcement**: Primary key constraint on `message_id`
- **Graceful handling**: Catches `IntegrityError` and returns 200 with same response
- **Metrics tracking**: Separate counter for duplicate vs created messages
- **No stack traces**: Duplicates are expected behavior, not errors

### Structured Logging

- **JSON format**: One JSON object per line for easy parsing with `jq` or log aggregators
- **Request ID**: Unique ID per request for tracing across logs
- **Context propagation**: Uses `contextvars` for async-safe request ID storage
- **Rich metadata**: Includes method, path, status, latency, and webhook-specific fields

## Repository Structure

```
/
├── app/
│   ├── main.py           # FastAPI application and endpoints
│   ├── models.py         # Pydantic models for validation
│   ├── storage.py        # Async SQLite storage layer
│   ├── logging_utils.py  # Structured JSON logging
│   ├── metrics.py        # Prometheus metrics collector
│   └── config.py         # Environment configuration
├── tests/
│   ├── test_webhook.py   # Webhook endpoint tests
│   ├── test_messages.py  # Messages endpoint tests
│   └── test_stats.py     # Stats endpoint tests
├── Dockerfile            # Multi-stage Docker build
├── docker-compose.yml    # Docker Compose configuration
├── Makefile              # Convenience commands
├── pyproject.toml        # Poetry dependencies
├── requirements.txt      # Pip dependencies
└── README.md             # This file
```

## Setup Used

This project was developed using:
- **VSCode** as the primary IDE
- **GitHub Copilot** for code completion and suggestions
- **Occasional ChatGPT prompts** for design decisions and documentation

## Troubleshooting

### Service won't start

- Check that `WEBHOOK_SECRET` is set: `docker compose logs api`
- Verify database directory permissions: `ls -la data/`

### Signature verification fails

- Ensure you're using raw body bytes for signature computation
- Verify the secret matches between client and server
- Check that signature is lowercase hex string

### Tests fail

- Ensure test database is writable: `mkdir -p data && chmod 777 data`
- Check that `WEBHOOK_SECRET` is set in test environment
- Run with verbose output: `pytest tests/ -vv`

## License

MIT
#   f a s t a p i - w e b h o o k - s e r v i c e  
 