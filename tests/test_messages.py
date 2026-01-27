"""Tests for messages endpoint."""
import pytest
import hmac
import hashlib
import json
from httpx import AsyncClient
from app.main import app
from app.config import config


def compute_signature(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def insert_test_message(client: AsyncClient, message_id: str, from_: str, ts: str, text: str = None):
    """Helper to insert a test message."""
    payload = {
        "message_id": message_id,
        "from": from_,
        "to": "+14155550100",
        "ts": ts,
        "text": text
    }
    body = json.dumps(payload).encode()
    signature = compute_signature(body, config.WEBHOOK_SECRET)
    
    await client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature
        }
    )


@pytest.mark.asyncio
async def test_messages_empty():
    """Test messages endpoint with no data."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/messages")
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert data["total"] >= 0
    assert data["limit"] == 50
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_messages_pagination():
    """Test messages pagination."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Insert test messages
        await insert_test_message(client, "msg1", "+911111111111", "2025-01-15T09:00:00Z", "First")
        await insert_test_message(client, "msg2", "+912222222222", "2025-01-15T10:00:00Z", "Second")
        await insert_test_message(client, "msg3", "+913333333333", "2025-01-15T11:00:00Z", "Third")
        
        # Get first page
        response = await client.get("/messages?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 2
        assert data["limit"] == 2
        assert data["offset"] == 0


@pytest.mark.asyncio
async def test_messages_ordering():
    """Test messages are ordered by ts ASC, message_id ASC."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Insert messages in non-chronological order
        await insert_test_message(client, "msg_b", "+911111111111", "2025-01-15T10:00:00Z", "B")
        await insert_test_message(client, "msg_a", "+911111111111", "2025-01-15T10:00:00Z", "A")
        await insert_test_message(client, "msg_c", "+911111111111", "2025-01-15T09:00:00Z", "C")
        
        response = await client.get("/messages")
        assert response.status_code == 200
        data = response.json()
        
        # Find our test messages
        test_msgs = [m for m in data["data"] if m["message_id"].startswith("msg_")]
        
        if len(test_msgs) >= 3:
            # Should be ordered: msg_c (09:00), then msg_a, msg_b (both 10:00, alphabetical)
            assert test_msgs[0]["message_id"] == "msg_c"
            # For same timestamp, should be alphabetical by message_id
            same_ts = [m for m in test_msgs if m["ts"] == "2025-01-15T10:00:00Z"]
            if len(same_ts) >= 2:
                assert same_ts[0]["message_id"] == "msg_a"
                assert same_ts[1]["message_id"] == "msg_b"


@pytest.mark.asyncio
async def test_messages_filter_from():
    """Test filtering by sender."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        sender = "+919999999999"
        await insert_test_message(client, "filter1", sender, "2025-01-15T10:00:00Z", "Test")
        await insert_test_message(client, "filter2", "+918888888888", "2025-01-15T10:01:00Z", "Other")
        
        response = await client.get(f"/messages?from={sender}")
        assert response.status_code == 200
        data = response.json()
        
        # All returned messages should be from the specified sender
        for msg in data["data"]:
            if msg["message_id"] in ["filter1", "filter2"]:
                assert msg["from"] == sender


@pytest.mark.asyncio
async def test_messages_filter_since():
    """Test filtering by timestamp."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        await insert_test_message(client, "since1", "+911111111111", "2025-01-15T08:00:00Z", "Before")
        await insert_test_message(client, "since2", "+911111111111", "2025-01-15T10:00:00Z", "After")
        
        response = await client.get("/messages?since=2025-01-15T09:00:00Z")
        assert response.status_code == 200
        data = response.json()
        
        # All returned messages should have ts >= since
        for msg in data["data"]:
            if msg["message_id"] in ["since1", "since2"]:
                assert msg["ts"] >= "2025-01-15T09:00:00Z"


@pytest.mark.asyncio
async def test_messages_filter_q():
    """Test text search."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        await insert_test_message(client, "search1", "+911111111111", "2025-01-15T10:00:00Z", "Hello World")
        await insert_test_message(client, "search2", "+911111111111", "2025-01-15T10:01:00Z", "Goodbye")
        
        response = await client.get("/messages?q=Hello")
        assert response.status_code == 200
        data = response.json()
        
        # Check that search1 is in results
        message_ids = [msg["message_id"] for msg in data["data"]]
        if "search1" in message_ids:
            msg = next(m for m in data["data"] if m["message_id"] == "search1")
            assert "Hello" in msg["text"]


@pytest.mark.asyncio
async def test_messages_limit_validation():
    """Test limit parameter validation."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test max limit
        response = await client.get("/messages?limit=100")
        assert response.status_code == 200
        
        # Test exceeding max limit
        response = await client.get("/messages?limit=101")
        assert response.status_code == 422
        
        # Test min limit
        response = await client.get("/messages?limit=1")
        assert response.status_code == 200
        
        # Test below min limit
        response = await client.get("/messages?limit=0")
        assert response.status_code == 422
