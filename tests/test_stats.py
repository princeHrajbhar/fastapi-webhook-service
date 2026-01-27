"""Tests for stats endpoint."""
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
async def test_stats_empty():
    """Test stats with no messages."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/stats")
    
    assert response.status_code == 200
    data = response.json()
    assert "total_messages" in data
    assert "senders_count" in data
    assert "messages_per_sender" in data
    assert isinstance(data["messages_per_sender"], list)
    # Timestamps should be null when no messages
    if data["total_messages"] == 0:
        assert data["first_message_ts"] is None
        assert data["last_message_ts"] is None


@pytest.mark.asyncio
async def test_stats_with_messages():
    """Test stats with messages."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Insert test messages
        await insert_test_message(client, "stat1", "+911111111111", "2025-01-15T09:00:00Z", "First")
        await insert_test_message(client, "stat2", "+911111111111", "2025-01-15T10:00:00Z", "Second")
        await insert_test_message(client, "stat3", "+912222222222", "2025-01-15T11:00:00Z", "Third")
        
        response = await client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_messages"] >= 3
        assert data["senders_count"] >= 2
        assert len(data["messages_per_sender"]) > 0
        assert data["first_message_ts"] is not None
        assert data["last_message_ts"] is not None


@pytest.mark.asyncio
async def test_stats_messages_per_sender_ordering():
    """Test that messages_per_sender is ordered by count DESC."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Insert messages from different senders
        sender1 = "+917777777777"
        sender2 = "+918888888888"
        
        # Sender1: 3 messages
        await insert_test_message(client, "order1", sender1, "2025-01-15T10:00:00Z", "A")
        await insert_test_message(client, "order2", sender1, "2025-01-15T10:01:00Z", "B")
        await insert_test_message(client, "order3", sender1, "2025-01-15T10:02:00Z", "C")
        
        # Sender2: 1 message
        await insert_test_message(client, "order4", sender2, "2025-01-15T10:03:00Z", "D")
        
        response = await client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Find our test senders
        test_senders = [s for s in data["messages_per_sender"] if s["from"] in [sender1, sender2]]
        
        if len(test_senders) >= 2:
            # Should be ordered by count descending
            counts = [s["count"] for s in test_senders]
            assert counts == sorted(counts, reverse=True)


@pytest.mark.asyncio
async def test_stats_top_10_senders():
    """Test that only top 10 senders are returned."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Should return at most 10 senders
        assert len(data["messages_per_sender"]) <= 10


@pytest.mark.asyncio
async def test_stats_timestamps():
    """Test first and last message timestamps."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Insert messages with known timestamps
        await insert_test_message(client, "ts1", "+911111111111", "2025-01-15T08:00:00Z", "Early")
        await insert_test_message(client, "ts2", "+911111111111", "2025-01-15T12:00:00Z", "Late")
        
        response = await client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Timestamps should be set
        assert data["first_message_ts"] is not None
        assert data["last_message_ts"] is not None
        
        # Last should be >= first
        assert data["last_message_ts"] >= data["first_message_ts"]
