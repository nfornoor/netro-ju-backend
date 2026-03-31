from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str = ""

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    smtp_from_name: str = "নেত্রকোণা জাহাঙ্গীরনগর"
    smtp_from_email: str

    admin_email: str = "hnur8873@gmail.com"
    frontend_url: str = "http://localhost:5173"
    secret_key: str
    port: int = 8000

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
