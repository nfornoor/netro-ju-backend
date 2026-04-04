from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class SignupRequest(BaseModel):
    full_name: str
    batch: str
    phone_number: str
    upazila: str
    village: Optional[str] = None
    email: EmailStr
    department: str
    blood_group: Optional[str] = None
    hall: Optional[str] = None
    school: Optional[str] = None
    college: Optional[str] = None
    password: str
    confirm_password: str


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str


class LoginRequest(BaseModel):
    phone_number: str
    password: str


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    batch: Optional[str] = None
    upazila: Optional[str] = None
    village: Optional[str] = None
    department: Optional[str] = None
    blood_group: Optional[str] = None
    hall: Optional[str] = None
    school: Optional[str] = None
    college: Optional[str] = None


class ProfileResponse(BaseModel):
    id: str
    full_name: str
    batch: str
    phone_number: str
    upazila: str
    village: Optional[str]
    email: str
    department: str
    profile_picture: Optional[str]
    blood_group: Optional[str]
    hall: Optional[str]
    school: Optional[str]
    college: Optional[str]
    role: str
    is_email_verified: bool
    is_approved: bool
    created_at: datetime
