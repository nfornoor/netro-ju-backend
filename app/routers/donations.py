from fastapi import APIRouter, HTTPException, Depends
from ..database import supabase_admin
from ..models.donation import DonationCreate, DonationStatusUpdate
from ..dependencies import get_current_user, get_admin_user

router = APIRouter(prefix="/api/donations", tags=["donations"])


@router.post("")
async def create_donation(data: DonationCreate, current_user: dict = Depends(get_current_user)):
    payload = data.model_dump()
    if current_user:
        payload["user_id"] = current_user["id"]

    result = supabase_admin.table("donations").insert(payload).execute()
    return result.data[0]


@router.post("/guest")
async def create_guest_donation(data: DonationCreate):
    """Donation without authentication"""
    result = supabase_admin.table("donations").insert(data.model_dump()).execute()
    return result.data[0]


@router.get("")
async def get_my_donations(current_user: dict = Depends(get_current_user)):
    result = supabase_admin.table("donations") \
        .select("*") \
        .eq("user_id", current_user["id"]) \
        .order("created_at", desc=True) \
        .execute()
    return result.data


@router.get("/all")
async def get_all_donations(admin: dict = Depends(get_admin_user)):
    result = supabase_admin.table("donations") \
        .select("*, profiles(full_name, phone_number)") \
        .order("created_at", desc=True) \
        .execute()
    return result.data


@router.put("/{donation_id}/status")
async def update_donation_status(
    donation_id: str,
    data: DonationStatusUpdate,
    admin: dict = Depends(get_admin_user)
):
    if data.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")

    payload = {"status": data.status}
    if data.admin_notes:
        payload["admin_notes"] = data.admin_notes

    result = supabase_admin.table("donations").update(payload).eq("id", donation_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Donation not found")
    return result.data[0]
