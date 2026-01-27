"""FastAPI application main entry point."""
import hmac
import hashlib
import logging
import time
from typing import Optional
from fastapi import FastAPI, Request, Response, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from contextlib import asynccontextmanager

from app.config import config
from app.models import (
    WebhookRequest, WebhookResponse, MessagesResponse,
    StatsResponse, MessageOut
)
from app.storage import Storage
from app.logging_utils import (
    setup_logging, generate_request_id, set_request_id, get_request_id
)
from app.metrics import metrics


# Initialize logging
setup_logging(config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize storage
storage = Storage(config.DATABASE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    validation_error = config.validate()
    if validation_error:
        logger.error(validation_error)
        raise RuntimeError(validation_error)
    
    await storage.init_db()
    logger.info("Application started")
    
    yield
    
    # Shutdown
    logger.info("Application shutting down")


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Middleware for request logging and metrics."""
    request_id = generate_request_id()
    set_request_id(request_id)
    
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate latency
    latency_ms = round((time.time() - start_time) * 1000, 2)
    
    # Record metrics
    metrics.record_http_request(request.url.path, response.status_code)
    metrics.record_latency(latency_ms)
    
    # Log request
    log_extra = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "latency_ms": latency_ms
    }
    
    logger.info(
        f"{request.method} {request.url.path} {response.status_code}",
        extra=log_extra
    )
    
    return response


def verify_signature(body: bytes, signature: str) -> bool:
    """Verify HMAC-SHA256 signature using constant-time comparison."""
    expected = hmac.new(
        config.WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)


@app.post("/webhook", response_model=WebhookResponse)
async def webhook(request: Request):
    """Ingest inbound WhatsApp-like messages."""
    # Read raw body
    body = await request.body()
    
    # Verify signature
    signature = request.headers.get("X-Signature", "")
    if not verify_signature(body, signature):
        log_extra = {
            "request_id": get_request_id(),
            "result": "invalid_signature"
        }
        logger.error("Invalid signature", extra=log_extra)
        metrics.record_webhook_request("invalid_signature")
        raise HTTPException(status_code=401, detail="invalid signature")
    
    # Parse and validate payload
    try:
        payload = WebhookRequest.model_validate_json(body)
    except Exception as e:
        log_extra = {
            "request_id": get_request_id(),
            "result": "validation_error"
        }
        logger.error(f"Validation error: {str(e)}", extra=log_extra)
        metrics.record_webhook_request("validation_error")
        raise
    
    # Insert into database
    success, is_duplicate = await storage.insert_message(
        message_id=payload.message_id,
        from_msisdn=payload.from_,
        to_msisdn=payload.to,
        ts=payload.ts,
        text=payload.text
    )
    
    # Log and record metrics
    result = "duplicate" if is_duplicate else "created"
    log_extra = {
        "request_id": get_request_id(),
        "message_id": payload.message_id,
        "dup": is_duplicate,
        "result": result
    }
    logger.info(f"Webhook processed: {result}", extra=log_extra)
    metrics.record_webhook_request(result)
    
    return WebhookResponse(status="ok")


@app.get("/messages", response_model=MessagesResponse)
async def get_messages(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    from_: Optional[str] = Query(default=None, alias="from"),
    since: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None)
):
    """Get paginated and filtered messages."""
    messages, total = await storage.get_messages(
        limit=limit,
        offset=offset,
        from_filter=from_,
        since=since,
        q=q
    )
    
    return MessagesResponse(
        data=[MessageOut(**msg) for msg in messages],
        total=total,
        limit=limit,
        offset=offset
    )


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get message statistics."""
    stats = await storage.get_stats()
    return StatsResponse(**stats)


@app.get("/health/live")
async def health_live():
    """Liveness probe - always returns 200 when app is running."""
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    """Readiness probe - returns 200 only when fully ready."""
    # Check WEBHOOK_SECRET
    if not config.WEBHOOK_SECRET:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "reason": "WEBHOOK_SECRET not set"}
        )
    
    # Check database
    if not await storage.is_ready():
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "reason": "database not ready"}
        )
    
    return {"status": "ready"}


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return PlainTextResponse(
        content=metrics.export_metrics(),
        media_type="text/plain; version=0.0.4"
    )
