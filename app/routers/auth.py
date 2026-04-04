import random
import string
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import Optional
from ..database import supabase, supabase_admin
from ..email_utils import send_otp_email, send_admin_new_user_notification
from ..models.user import SignupRequest, VerifyEmailRequest, LoginRequest
from ..dependencies import get_current_user
from ..config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


@router.post("/signup")
async def signup(
    full_name: str = Form(...),
    batch: str = Form(...),
    phone_number: str = Form(...),
    upazila: str = Form(...),
    village: Optional[str] = Form(None),
    email: str = Form(...),
    department: str = Form(...),
    blood_group: Optional[str] = Form(None),
    hall: Optional[str] = Form(None),
    school: Optional[str] = Form(None),
    college: Optional[str] = Form(None),
    password: str = Form(...),
    confirm_password: str = Form(...),
    profile_picture: Optional[UploadFile] = File(None),
):
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Check for existing phone/email
    existing_phone = supabase_admin.table("profiles").select("id").eq("phone_number", phone_number).execute()
    if existing_phone.data:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    existing_email = supabase_admin.table("profiles").select("id").eq("email", email).execute()
    if existing_email.data:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Upload profile picture if provided (skip silently if storage bucket missing)
    picture_url = None
    if profile_picture and profile_picture.filename:
        try:
            contents = await profile_picture.read()
            ext = profile_picture.filename.rsplit(".", 1)[-1].lower()
            filename = f"{phone_number}_{datetime.now().timestamp()}.{ext}"
            supabase_admin.storage.from_("profile-pictures").upload(
                filename, contents, {"content-type": profile_picture.content_type}
            )
            picture_url = f"{settings.supabase_url}/storage/v1/object/public/profile-pictures/{filename}"
        except Exception:
            pass  # Storage bucket not created yet — skip profile picture

    # Create Supabase Auth user
    try:
        auth_res = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": False,
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    user_id = auth_res.user.id

    # Insert profile
    try:
        supabase_admin.table("profiles").insert({
            "id": user_id,
            "full_name": full_name,
            "batch": batch,
            "phone_number": phone_number,
            "upazila": upazila,
            "village": village,
            "email": email,
            "department": department,
            "blood_group": blood_group,
            "hall": hall,
            "school": school,
            "college": college,
            "profile_picture": picture_url,
            "role": "pending",
            "is_email_verified": False,
            "is_approved": False,
        }).execute()
    except Exception as e:
        supabase_admin.auth.admin.delete_user(user_id)
        raise HTTPException(status_code=500, detail=f"Profile insert failed: {str(e)}")

    # Generate and store OTP
    try:
        otp = generate_otp()
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        supabase_admin.table("email_otps").insert({
            "email": email,
            "otp": otp,
            "expires_at": expires_at,
            "used": False,
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OTP generation failed: {str(e)}")

    # Send OTP email
    try:
        await send_otp_email(email, full_name, otp)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")

    return {"message": "Registration successful. Please check your email for the verification code.", "email": email}


@router.post("/verify-email")
async def verify_email(data: VerifyEmailRequest):
    now = datetime.now(timezone.utc)

    # Find valid OTP
    result = supabase_admin.table("email_otps") \
        .select("*") \
        .eq("email", data.email) \
        .eq("otp", data.otp) \
        .eq("used", False) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    otp_record = result.data[0]
    expires_at = datetime.fromisoformat(otp_record["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now > expires_at:
        raise HTTPException(status_code=400, detail="Verification code has expired")

    # Mark OTP as used
    supabase_admin.table("email_otps").update({"used": True}).eq("id", otp_record["id"]).execute()

    # Update profile
    profile_res = supabase_admin.table("profiles") \
        .update({"is_email_verified": True}) \
        .eq("email", data.email) \
        .execute()

    if not profile_res.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = profile_res.data[0]

    # Confirm email in Supabase Auth
    supabase_admin.auth.admin.update_user_by_id(
        profile["id"],
        {"email_confirm": True}
    )

    # Notify admin
    await send_admin_new_user_notification(
        profile["full_name"], profile["email"],
        profile["phone_number"], profile["batch"], profile["department"]
    )

    return {"message": "Email verified. Your account is pending admin approval."}


@router.post("/resend-otp")
async def resend_otp(email: str):
    profile = supabase_admin.table("profiles").select("*").eq("email", email).single().execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Email not found")
    if profile.data.get("is_email_verified"):
        raise HTTPException(status_code=400, detail="Email already verified")

    otp = generate_otp()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    supabase_admin.table("email_otps").insert({
        "email": email,
        "otp": otp,
        "expires_at": expires_at,
        "used": False,
    }).execute()

    await send_otp_email(email, profile.data["full_name"], otp)
    return {"message": "New verification code sent"}


@router.post("/admin-login")
async def admin_login(email: str, password: str):
    """Direct email+password login for the admin account."""
    profile_res = supabase_admin.table("profiles") \
        .select("email, is_email_verified, is_approved, role") \
        .eq("email", email) \
        .eq("role", "admin") \
        .single() \
        .execute()

    if not profile_res.data:
        raise HTTPException(status_code=401, detail="Not an admin account")

    try:
        auth_res = supabase.auth.sign_in_with_password({"email": email, "password": password})
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
        "access_token": auth_res.session.access_token,
        "refresh_token": auth_res.session.refresh_token,
        "token_type": "bearer",
    }


@router.post("/login")
async def login(data: LoginRequest):
    # Look up email by phone number
    profile_res = supabase_admin.table("profiles") \
        .select("email, is_email_verified, is_approved, role") \
        .eq("phone_number", data.phone_number) \
        .single() \
        .execute()

    if not profile_res.data:
        raise HTTPException(status_code=401, detail="Invalid phone number or password")

    profile = profile_res.data

    if not profile.get("is_email_verified"):
        raise HTTPException(status_code=403, detail="Please verify your email first")

    if not profile.get("is_approved"):
        raise HTTPException(status_code=403, detail="Your account is pending admin approval")

    # Authenticate with Supabase
    try:
        auth_res = supabase.auth.sign_in_with_password({
            "email": profile["email"],
            "password": data.password,
        })
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid phone number or password")

    return {
        "access_token": auth_res.session.access_token,
        "refresh_token": auth_res.session.refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    try:
        res = supabase.auth.refresh_session(refresh_token)
        return {
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token,
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user
