"""Tests for webhook endpoint."""
import pytest
import hmac
import hashlib
import json
from httpx import AsyncClient
from app.main import app
from app.config import config


@pytest.fixture
def webhook_payload():
    """Sample webhook payload."""
    return {
        "message_id": "m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    }


def compute_signature(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_webhook_valid_signature(webhook_payload):
    """Test webhook with valid signature."""
    body = json.dumps(webhook_payload).encode()
    signature = compute_signature(body, config.WEBHOOK_SECRET)
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature
            }
        )
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_webhook_invalid_signature(webhook_payload):
    """Test webhook with invalid signature."""
    body = json.dumps(webhook_payload).encode()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": "invalid"
            }
        )
    
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid signature"}


@pytest.mark.asyncio
async def test_webhook_missing_signature(webhook_payload):
    """Test webhook with missing signature."""
    body = json.dumps(webhook_payload).encode()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/webhook",
            content=body,
            headers={"Content-Type": "application/json"}
        )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_idempotency(webhook_payload):
    """Test webhook idempotency - duplicate message_id."""
    body = json.dumps(webhook_payload).encode()
    signature = compute_signature(body, config.WEBHOOK_SECRET)
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First request
        response1 = await client.post(
            "/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature
            }
        )
        
        # Second request with same message_id
        response2 = await client.post(
            "/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature
            }
        )
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == {"status": "ok"}
    assert response2.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_webhook_invalid_e164():
    """Test webhook with invalid E.164 format."""
    payload = {
        "message_id": "m2",
        "from": "invalid",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Test"
    }
    body = json.dumps(payload).encode()
    signature = compute_signature(body, config.WEBHOOK_SECRET)
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature
            }
        )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_webhook_invalid_timestamp():
    """Test webhook with invalid timestamp format."""
    payload = {
        "message_id": "m3",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00",  # Missing Z
        "text": "Test"
    }
    body = json.dumps(payload).encode()
    signature = compute_signature(body, config.WEBHOOK_SECRET)
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature
            }
        )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_webhook_text_too_long():
    """Test webhook with text exceeding max length."""
    payload = {
        "message_id": "m4",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "x" * 4097  # Exceeds 4096 limit
    }
    body = json.dumps(payload).encode()
    signature = compute_signature(body, config.WEBHOOK_SECRET)
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Signature": signature
            }
        )
    
    assert response.status_code == 422
