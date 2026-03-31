from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from ..database import supabase_admin
from ..models.notice import NoticeCreate, NoticeUpdate
from ..dependencies import get_current_user, get_approved_member, get_admin_user
from ..email_utils import send_notice_notification
from datetime import datetime

router = APIRouter(prefix="/api/notices", tags=["notices"])


@router.get("")
async def get_notices(current_user: dict = Depends(get_current_user)):
    is_member = current_user and current_user.get("role") in ("member", "admin")

    query = supabase_admin.table("notices").select("*, profiles(full_name)").eq("is_published", True)

    if not is_member:
        query = query.eq("visibility", "public")

    result = query.order("created_at", desc=True).execute()
    return result.data


@router.get("/public")
async def get_public_notices():
    result = supabase_admin.table("notices") \
        .select("id, title, content, type, visibility, event_date, attachment_url, show_donation_button, created_at") \
        .eq("is_published", True) \
        .eq("visibility", "public") \
        .order("created_at", desc=True) \
        .limit(20) \
        .execute()
    return result.data


@router.get("/{notice_id}")
async def get_notice(notice_id: str, current_user: dict = Depends(get_current_user)):
    result = supabase_admin.table("notices").select("*").eq("id", notice_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Notice not found")

    notice = result.data
    if notice["visibility"] == "members_only":
        if not current_user or current_user.get("role") not in ("member", "admin"):
            raise HTTPException(status_code=403, detail="Members only")

    return notice


@router.post("")
async def create_notice(data: NoticeCreate, admin: dict = Depends(get_admin_user)):
    payload = data.model_dump()
    payload["created_by"] = admin["id"]
    if payload.get("event_date") and isinstance(payload["event_date"], datetime):
        payload["event_date"] = payload["event_date"].isoformat()

    result = supabase_admin.table("notices").insert(payload).execute()
    notice = result.data[0]

    # Notify members if published
    if data.is_published:
        members = supabase_admin.table("profiles") \
            .select("email") \
            .in_("role", ["member", "admin"]) \
            .execute()
        emails = [m["email"] for m in (members.data or []) if m.get("email")]

        # For members_only notices, only notify members
        # For public notices, notify all members
        if emails:
            await send_notice_notification(emails, data.title, data.content, data.type, data.show_donation_button)

    return notice


@router.put("/{notice_id}")
async def update_notice(notice_id: str, data: NoticeUpdate, admin: dict = Depends(get_admin_user)):
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    if "event_date" in payload and isinstance(payload["event_date"], datetime):
        payload["event_date"] = payload["event_date"].isoformat()

    result = supabase_admin.table("notices").update(payload).eq("id", notice_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Notice not found")
    return result.data[0]


@router.delete("/{notice_id}")
async def delete_notice(notice_id: str, admin: dict = Depends(get_admin_user)):
    supabase_admin.table("notices").delete().eq("id", notice_id).execute()
    return {"message": "Notice deleted"}


@router.post("/{notice_id}/attachment")
async def upload_attachment(notice_id: str, file: UploadFile = File(...), admin: dict = Depends(get_admin_user)):
    contents = await file.read()
    ext = file.filename.rsplit(".", 1)[-1].lower()
    filename = f"{notice_id}.{ext}"
    supabase_admin.storage.from_("notice-attachments").upload(
        filename, contents, {"content-type": file.content_type}
    )
    url = supabase_admin.storage.from_("notice-attachments").get_public_url(filename)
    supabase_admin.table("notices").update({"attachment_url": url}).eq("id", notice_id).execute()
    return {"attachment_url": url}
