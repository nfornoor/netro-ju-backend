from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NoticeCreate(BaseModel):
    title: str
    content: str
    type: str = "notice"  # "notice" | "event"
    visibility: str = "public"  # "public" | "members_only"
    event_date: Optional[datetime] = None
    attachment_url: Optional[str] = None
    is_published: bool = True
    show_donation_button: bool = False


class NoticeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    type: Optional[str] = None
    visibility: Optional[str] = None
    event_date: Optional[datetime] = None
    attachment_url: Optional[str] = None
    is_published: Optional[bool] = None
    show_donation_button: Optional[bool] = None


class NoticeResponse(BaseModel):
    id: str
    title: str
    content: str
    type: str
    visibility: str
    event_date: Optional[datetime]
    attachment_url: Optional[str]
    created_by: Optional[str]
    is_published: bool
    created_at: datetime
    updated_at: datetime
