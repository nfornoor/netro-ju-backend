from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from ..database import supabase_admin
from ..models.user import ProfileUpdate
from ..dependencies import get_current_user, get_approved_member
from ..config import get_settings
from datetime import datetime

settings = get_settings()

router = APIRouter(prefix="/api/members", tags=["members"])


@router.get("")
async def get_members(member: dict = Depends(get_approved_member)):
    result = supabase_admin.table("profiles") \
        .select("id, full_name, batch, phone_number, upazila, village, email, department, profile_picture, blood_group, hall, school, college, role, created_at") \
        .in_("role", ["member", "admin"]) \
        .order("full_name") \
        .execute()
    members = result.data or []

    # Attach committee positions
    committee = supabase_admin.table("committee_members") \
        .select("user_id, position") \
        .execute()
    committee_map = {c["user_id"]: c["position"] for c in (committee.data or []) if c.get("user_id")}
    for m in members:
        m["committee_position"] = committee_map.get(m["id"])

    return members


@router.get("/{member_id}")
async def get_member(member_id: str, current_user: dict = Depends(get_approved_member)):
    result = supabase_admin.table("profiles") \
        .select("id, full_name, batch, phone_number, upazila, village, email, department, profile_picture, blood_group, hall, school, college, role, created_at") \
        .eq("id", member_id) \
        .single() \
        .execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Member not found")
    return result.data


@router.put("/me")
async def update_my_profile(data: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    result = supabase_admin.table("profiles").update(payload).eq("id", current_user["id"]).execute()
    return result.data[0]


@router.post("/me/picture")
async def update_profile_picture(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    contents = await file.read()
    ext = file.filename.rsplit(".", 1)[-1].lower()
    filename = f"{current_user['id']}.{ext}"
    try:
        # Try upsert (overwrite existing file)
        supabase_admin.storage.from_("profile-pictures").upload(
            filename, contents, {"content-type": file.content_type, "upsert": "true"}
        )
    except Exception:
        # File may already exist — remove then re-upload
        try:
            supabase_admin.storage.from_("profile-pictures").remove([filename])
        except Exception:
            pass
        supabase_admin.storage.from_("profile-pictures").upload(
            filename, contents, {"content-type": file.content_type}
        )
    url = f"{settings.supabase_url}/storage/v1/object/public/profile-pictures/{filename}"
    supabase_admin.table("profiles").update({"profile_picture": url}).eq("id", current_user["id"]).execute()
    return {"profile_picture": url}
