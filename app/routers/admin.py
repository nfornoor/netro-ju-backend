from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from ..database import supabase_admin
from ..dependencies import get_admin_user
from ..email_utils import send_approval_email, send_rejection_email
from ..config import get_settings
from datetime import datetime

settings = get_settings()

router = APIRouter(prefix="/api/admin", tags=["admin"])

MAIN_ADMIN_PHONE = "01902960870"


# ─── Users ───────────────────────────────────────────────────────────────────

@router.get("/pending-users")
async def get_pending_users(admin: dict = Depends(get_admin_user)):
    result = supabase_admin.table("profiles") \
        .select("*") \
        .eq("role", "pending") \
        .eq("is_email_verified", True) \
        .order("created_at") \
        .execute()
    return result.data


@router.put("/users/{user_id}/approve")
async def approve_user(user_id: str, admin: dict = Depends(get_admin_user)):
    result = supabase_admin.table("profiles") \
        .update({"role": "member", "is_approved": True}) \
        .eq("id", user_id) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = result.data[0]
    try:
        await send_approval_email(user["email"], user["full_name"])
    except Exception:
        pass  # approval succeeds even if email fails
    return {"message": f"{user['full_name']} approved"}


@router.put("/users/{user_id}/reject")
async def reject_user(user_id: str, reason: Optional[str] = None, admin: dict = Depends(get_admin_user)):
    result = supabase_admin.table("profiles").select("*").eq("id", user_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = result.data
    # Delete from Supabase Auth and profiles
    supabase_admin.auth.admin.delete_user(user_id)
    await send_rejection_email(user["email"], user["full_name"], reason or "")
    return {"message": f"{user['full_name']} rejected and removed"}


@router.get("/users")
async def get_all_users(admin: dict = Depends(get_admin_user)):
    result = supabase_admin.table("profiles") \
        .select("*") \
        .order("created_at", desc=True) \
        .execute()
    return result.data


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(get_admin_user)):
    result = supabase_admin.table("profiles").select("full_name, phone_number").eq("id", user_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    if result.data.get("phone_number") == MAIN_ADMIN_PHONE:
        raise HTTPException(status_code=403, detail="প্রধান অ্যাডমিনকে মুছে ফেলা যাবে না")
    supabase_admin.auth.admin.delete_user(user_id)
    return {"message": f"{result.data['full_name']} deleted"}


@router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, role: str, admin: dict = Depends(get_admin_user)):
    if role not in ("member", "admin", "pending"):
        raise HTTPException(status_code=400, detail="Invalid role")
    result = supabase_admin.table("profiles").select("phone_number").eq("id", user_id).single().execute()
    if result.data and result.data.get("phone_number") == MAIN_ADMIN_PHONE:
        raise HTTPException(status_code=403, detail="প্রধান অ্যাডমিনের ভূমিকা পরিবর্তন করা যাবে না")
    result = supabase_admin.table("profiles").update({"role": role}).eq("id", user_id).execute()
    return result.data[0]


# ─── Committee ───────────────────────────────────────────────────────────────

class CommitteeMemberCreate(BaseModel):
    user_id: Optional[str] = None
    name: str
    position: str
    photo_url: Optional[str] = None
    batch: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    display_order: int = 0


class CommitteeMemberUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[str] = None
    photo_url: Optional[str] = None
    batch: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    display_order: Optional[int] = None


@router.get("/search-members")
async def search_members(q: str = "", admin: dict = Depends(get_admin_user)):
    if not q.strip():
        return []
    result = supabase_admin.table("profiles") \
        .select("id, full_name, batch, department, profile_picture, phone_number, upazila") \
        .in_("role", ["member", "admin"]) \
        .ilike("full_name", f"%{q}%") \
        .limit(10) \
        .execute()
    return result.data or []


@router.get("/committee")
async def get_committee(admin: dict = Depends(get_admin_user)):
    result = supabase_admin.table("committee_members") \
        .select("*, profiles(profile_picture, phone_number)") \
        .order("display_order") \
        .execute()
    data = result.data or []
    for member in data:
        linked = member.pop("profiles", None) or {}
        if not member.get("photo_url"):
            member["photo_url"] = linked.get("profile_picture")
        if not member.get("phone"):
            member["phone"] = linked.get("phone_number")
    return data


@router.post("/committee")
async def create_committee_member(data: CommitteeMemberCreate, admin: dict = Depends(get_admin_user)):
    result = supabase_admin.table("committee_members").insert(data.model_dump()).execute()
    return result.data[0]


@router.put("/committee/{member_id}")
async def update_committee_member(member_id: str, data: CommitteeMemberUpdate, admin: dict = Depends(get_admin_user)):
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    result = supabase_admin.table("committee_members").update(payload).eq("id", member_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Committee member not found")
    return result.data[0]


@router.delete("/committee/{member_id}")
async def delete_committee_member(member_id: str, admin: dict = Depends(get_admin_user)):
    supabase_admin.table("committee_members").delete().eq("id", member_id).execute()
    return {"message": "Deleted"}


@router.post("/committee/{member_id}/photo")
async def upload_committee_photo(member_id: str, file: UploadFile = File(...), admin: dict = Depends(get_admin_user)):
    contents = await file.read()
    ext = file.filename.rsplit(".", 1)[-1].lower()
    filename = f"{member_id}.{ext}"
    supabase_admin.storage.from_("committee-photos").upload(
        filename, contents, {"content-type": file.content_type, "upsert": "true"}
    )
    url = f"{settings.supabase_url}/storage/v1/object/public/committee-photos/{filename}"
    supabase_admin.table("committee_members").update({"photo_url": url}).eq("id", member_id).execute()
    return {"photo_url": url}


# ─── About Sections ──────────────────────────────────────────────────────────

class AboutSectionCreate(BaseModel):
    title: str
    content: str
    display_order: int = 0


class AboutSectionUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    display_order: Optional[int] = None


@router.get("/about")
async def get_about_sections(admin: dict = Depends(get_admin_user)):
    result = supabase_admin.table("about_sections").select("*").order("display_order").execute()
    return result.data


@router.post("/about")
async def create_about_section(data: AboutSectionCreate, admin: dict = Depends(get_admin_user)):
    payload = data.model_dump()
    payload["updated_by"] = admin["id"]
    result = supabase_admin.table("about_sections").insert(payload).execute()
    return result.data[0]


@router.put("/about/{section_id}")
async def update_about_section(section_id: str, data: AboutSectionUpdate, admin: dict = Depends(get_admin_user)):
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    payload["updated_by"] = admin["id"]
    result = supabase_admin.table("about_sections").update(payload).eq("id", section_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Section not found")
    return result.data[0]


@router.delete("/about/{section_id}")
async def delete_about_section(section_id: str, admin: dict = Depends(get_admin_user)):
    supabase_admin.table("about_sections").delete().eq("id", section_id).execute()
    return {"message": "Deleted"}


# ─── Site Settings ────────────────────────────────────────────────────────────

class SettingsUpdate(BaseModel):
    donation_enabled: Optional[bool] = None
    donation_description: Optional[str] = None


@router.get("/settings")
async def get_settings_admin(admin: dict = Depends(get_admin_user)):
    result = supabase_admin.table("site_settings").select("*").eq("id", 1).single().execute()
    return result.data


@router.put("/settings")
async def update_settings(data: SettingsUpdate, admin: dict = Depends(get_admin_user)):
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    result = supabase_admin.table("site_settings").update(payload).eq("id", 1).execute()
    return result.data[0]
