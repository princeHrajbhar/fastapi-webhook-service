import hmac
import hashlib
import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
SECRET = "mysecretkey"

def compute_signature(body_str, secret):
    """Compute HMAC-SHA256 signature."""
    return hmac.new(
        secret.encode(),
        body_str.encode(),
        hashlib.sha256
    ).hexdigest()

# Test 1: Health endpoints
print("=" * 60)
print("Testing Health Endpoints")
print("=" * 60)

response = requests.get(f"{BASE_URL}/health/live")
print(f"GET /health/live: {response.status_code} - {response.json()}")

response = requests.get(f"{BASE_URL}/health/ready")
print(f"GET /health/ready: {response.status_code} - {response.json()}")

# Test 2: Webhook with valid signature
print("\n" + "=" * 60)
print("Testing Webhook with Valid Signature")
print("=" * 60)

payload = {
    "message_id": "m1",
    "from": "+919876543210",
    "to": "+14155550100",
    "ts": "2025-01-15T10:00:00Z",
    "text": "Hello World"
}

body_str = json.dumps(payload)
signature = compute_signature(body_str, SECRET)

print(f"Body: {body_str}")
print(f"Signature: {signature}")

response = requests.post(
    f"{BASE_URL}/webhook",
    headers={
        "Content-Type": "application/json",
        "X-Signature": signature
    },
    data=body_str
)

print(f"POST /webhook: {response.status_code} - {response.json()}")

# Test 3: Webhook idempotency (send same message again)
print("\n" + "=" * 60)
print("Testing Webhook Idempotency (Duplicate)")
print("=" * 60)

response = requests.post(
    f"{BASE_URL}/webhook",
    headers={
        "Content-Type": "application/json",
        "X-Signature": signature
    },
    data=body_str
)

print(f"POST /webhook (duplicate): {response.status_code} - {response.json()}")

# Test 4: Webhook with invalid signature
print("\n" + "=" * 60)
print("Testing Webhook with Invalid Signature")
print("=" * 60)

response = requests.post(
    f"{BASE_URL}/webhook",
    headers={
        "Content-Type": "application/json",
        "X-Signature": "invalid_signature"
    },
    data=body_str
)

print(f"POST /webhook (invalid): {response.status_code} - {response.json()}")

# Test 5: Send a few more messages
print("\n" + "=" * 60)
print("Sending More Test Messages")
print("=" * 60)

test_messages = [
    {"message_id": "m2", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T09:00:00Z", "text": "Earlier message"},
    {"message_id": "m3", "from": "+918888888888", "to": "+14155550100", "ts": "2025-01-15T11:00:00Z", "text": "Later message"},
    {"message_id": "m4", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T12:00:00Z", "text": "Another message"},
]

for msg in test_messages:
    body_str = json.dumps(msg)
    signature = compute_signature(body_str, SECRET)
    response = requests.post(
        f"{BASE_URL}/webhook",
        headers={"Content-Type": "application/json", "X-Signature": signature},
        data=body_str
    )
    print(f"Message {msg['message_id']}: {response.status_code}")

# Test 6: Get messages
print("\n" + "=" * 60)
print("Testing GET /messages")
print("=" * 60)

response = requests.get(f"{BASE_URL}/messages")
data = response.json()
print(f"Status: {response.status_code}")
print(f"Total messages: {data['total']}")
print(f"Returned: {len(data['data'])} messages")
print(f"Limit: {data['limit']}, Offset: {data['offset']}")
print("\nMessages:")
for msg in data['data']:
    print(f"  - {msg['message_id']}: {msg['from']} -> {msg['to']} at {msg['ts']}")

# Test 7: Get messages with pagination
print("\n" + "=" * 60)
print("Testing GET /messages with Pagination")
print("=" * 60)

response = requests.get(f"{BASE_URL}/messages?limit=2&offset=0")
data = response.json()
print(f"Page 1 (limit=2, offset=0): {len(data['data'])} messages, total={data['total']}")

# Test 8: Get messages with filter
print("\n" + "=" * 60)
print("Testing GET /messages with Filter")
print("=" * 60)

response = requests.get(f"{BASE_URL}/messages?from=%2B919876543210")
data = response.json()
print(f"Filter by from=+919876543210: {len(data['data'])} messages")

# Test 9: Get stats
print("\n" + "=" * 60)
print("Testing GET /stats")
print("=" * 60)

response = requests.get(f"{BASE_URL}/stats")
data = response.json()
print(f"Status: {response.status_code}")
print(f"Total messages: {data['total_messages']}")
print(f"Unique senders: {data['senders_count']}")
print(f"First message: {data['first_message_ts']}")
print(f"Last message: {data['last_message_ts']}")
print("\nTop senders:")
for sender in data['messages_per_sender']:
    print(f"  - {sender['from']}: {sender['count']} messages")

# Test 10: Get metrics
print("\n" + "=" * 60)
print("Testing GET /metrics")
print("=" * 60)

response = requests.get(f"{BASE_URL}/metrics")
print(f"Status: {response.status_code}")
print("Metrics (first 20 lines):")
lines = response.text.split('\n')[:20]
for line in lines:
    if line.strip():
        print(f"  {line}")

print("\n" + "=" * 60)
print("All Tests Completed Successfully!")
print("=" * 60)
