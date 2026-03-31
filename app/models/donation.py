from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DonationCreate(BaseModel):
    name: str
    phone_number: str
    transaction_id: str
    amount: Optional[float] = None


class DonationStatusUpdate(BaseModel):
    status: str  # "approved" | "rejected"
    admin_notes: Optional[str] = None


class DonationResponse(BaseModel):
    id: str
    name: str
    phone_number: str
    transaction_id: str
    amount: Optional[float]
    status: str
    user_id: Optional[str]
    admin_notes: Optional[str]
    created_at: datetime
