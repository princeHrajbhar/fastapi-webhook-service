# Quick Reference Guide

## Service Status

✅ **Service is RUNNING** on http://localhost:8000

## Quick Commands

### Start/Stop Service
```bash
# Start service
docker compose up -d --build

# Stop service
docker compose down -v

# View logs
docker logs fastapi-webhook-service

# Follow logs
docker logs -f fastapi-webhook-service

# Check status
docker ps
```

### Test the API
```bash
# Run comprehensive tests
python test_webhook.py

# Or use curl (PowerShell)
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl http://localhost:8000/messages
curl http://localhost:8000/stats
curl http://localhost:8000/metrics
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| http://localhost:8000/webhook | POST | Ingest messages (requires signature) |
| http://localhost:8000/messages | GET | List messages (paginated) |
| http://localhost:8000/stats | GET | Get statistics |
| http://localhost:8000/health/live | GET | Liveness check |
| http://localhost:8000/health/ready | GET | Readiness check |
| http://localhost:8000/metrics | GET | Prometheus metrics |

## Example: Send a Webhook Message

Use the Python test script:
```bash
python test_webhook.py
```

Or manually with Python:
```python
import hmac
import hashlib
import requests
import json

SECRET = "mysecretkey"
BASE_URL = "http://localhost:8000"

payload = {
    "message_id": "test123",
    "from": "+919876543210",
    "to": "+14155550100",
    "ts": "2025-01-15T10:00:00Z",
    "text": "Hello from API"
}

body_str = json.dumps(payload)
signature = hmac.new(
    SECRET.encode(),
    body_str.encode(),
    hashlib.sha256
).hexdigest()

response = requests.post(
    f"{BASE_URL}/webhook",
    headers={
        "Content-Type": "application/json",
        "X-Signature": signature
    },
    data=body_str
)

print(response.status_code, response.json())
```

## Configuration

Environment variables (in `.env` file):
```
WEBHOOK_SECRET=mysecretkey
DATABASE_URL=sqlite:////data/app.db
LOG_LEVEL=INFO
```

## Database Location

SQLite database is stored at:
```
./data/app.db
```

## View Structured Logs

Logs are in JSON format:
```bash
# View logs
docker logs fastapi-webhook-service

# Parse with jq (if installed)
docker logs fastapi-webhook-service 2>&1 | grep "^{" | jq .

# Filter by level
docker logs fastapi-webhook-service 2>&1 | grep "^{" | jq 'select(.level=="ERROR")'
```

## Test Results Summary

✅ Health endpoints working  
✅ Webhook with valid signature: 200 OK  
✅ Webhook idempotency: 200 OK (duplicate)  
✅ Invalid signature: 401 Unauthorized  
✅ Messages listing: 200 OK  
✅ Pagination working  
✅ Filtering working  
✅ Stats endpoint: 200 OK  
✅ Metrics endpoint: 200 OK  
✅ Structured JSON logging active  

## Troubleshooting

### Service won't start
```bash
# Check Docker is running
docker ps

# Check logs
docker logs fastapi-webhook-service

# Rebuild
docker compose down -v
docker compose up -d --build
```

### Can't connect to API
```bash
# Check if port 8000 is available
netstat -an | findstr 8000

# Check container is running
docker ps | findstr fastapi
```

### Database issues
```bash
# Check database file
dir data\app.db

# Reset database
docker compose down -v
Remove-Item -Recurse -Force data
docker compose up -d --build
```

## Next Steps

1. ✅ Service is running
2. ✅ All tests passing
3. 📖 Read API.md for complete API documentation
4. 📖 Read DEPLOYMENT.md for production deployment
5. 🔧 Customize configuration in .env file
6. 🧪 Run your own tests with test_webhook.py

## Support Files

- `README.md` - Main documentation
- `API.md` - Complete API reference
- `TESTING.md` - Testing guide
- `DEPLOYMENT.md` - Production deployment
- `PROJECT_SUMMARY.md` - Project overview
- `VERIFICATION_CHECKLIST.md` - Specification compliance

## Current Status

🟢 **Service Running**: http://localhost:8000  
🟢 **Database**: ./data/app.db  
🟢 **Logs**: Structured JSON format  
🟢 **Tests**: All passing  
🟢 **Metrics**: Available at /metrics  

Enjoy your FastAPI webhook service! 🚀
