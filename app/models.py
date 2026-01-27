"""Pydantic models for request/response validation."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import re


class WebhookRequest(BaseModel):
    """Inbound webhook message payload."""
    message_id: str = Field(..., min_length=1)
    from_: str = Field(..., alias="from")
    to: str = Field(..., min_length=1)
    ts: str
    text: Optional[str] = Field(None, max_length=4096)
    
    @field_validator("from_", "to")
    @classmethod
    def validate_e164(cls, v: str) -> str:
        """Validate E.164 format: + followed by digits only."""
        if not re.match(r'^\+\d+$', v):
            raise ValueError("must be E.164 format: + followed by digits")
        return v
    
    @field_validator("ts")
    @classmethod
    def validate_iso8601_utc(cls, v: str) -> str:
        """Validate ISO-8601 UTC format with Z."""
        if not v.endswith("Z"):
            raise ValueError("timestamp must be ISO-8601 UTC with Z suffix")
        # Basic format check
        if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$', v):
            raise ValueError("timestamp must be ISO-8601 format: YYYY-MM-DDTHH:MM:SSZ")
        return v


class WebhookResponse(BaseModel):
    """Webhook endpoint response."""
    status: str = "ok"


class MessageOut(BaseModel):
    """Message representation in API responses."""
    message_id: str
    from_: str = Field(..., alias="from")
    to: str
    ts: str
    text: Optional[str]
    
    class Config:
        populate_by_name = True


class MessagesResponse(BaseModel):
    """Paginated messages list response."""
    data: List[MessageOut]
    total: int
    limit: int
    offset: int


class SenderCount(BaseModel):
    """Sender message count."""
    from_: str = Field(..., alias="from")
    count: int
    
    class Config:
        populate_by_name = True


class StatsResponse(BaseModel):
    """Statistics response."""
    total_messages: int
    senders_count: int
    messages_per_sender: List[SenderCount]
    first_message_ts: Optional[str]
    last_message_ts: Optional[str]
