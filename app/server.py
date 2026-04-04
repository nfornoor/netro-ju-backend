from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .routers import auth, notices, members, donations, admin

settings = get_settings()

app = FastAPI(
    title="Netro-JU API",
    description="Backend API for Gazipur District Union - Jahangirnagar University",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "https://nswa.netlify.app",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(notices.router)
app.include_router(members.router)
app.include_router(donations.router)
app.include_router(admin.router)


# Public endpoints (no auth required)
from .database import supabase_admin


@app.get("/")
async def root():
    return {"message": "Netro-JU API", "docs": "/docs"}


@app.get("/api/public/notices")
async def public_notices():
    result = supabase_admin.table("notices") \
        .select("id, title, content, type, visibility, event_date, attachment_url, show_donation_button, created_at") \
        .eq("is_published", True) \
        .eq("visibility", "public") \
        .order("created_at", desc=True) \
        .limit(10) \
        .execute()
    return result.data


@app.get("/api/public/committee")
async def public_committee():
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


@app.get("/api/public/about")
async def public_about():
    result = supabase_admin.table("about_sections") \
        .select("*") \
        .order("display_order") \
        .execute()
    return result.data


@app.get("/api/public/settings")
async def public_settings():
    result = supabase_admin.table("site_settings").select("*").eq("id", 1).single().execute()
    return result.data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.server:app", host="0.0.0.0", port=settings.port, reload=True)
