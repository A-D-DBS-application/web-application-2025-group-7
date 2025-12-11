import os
from importlib.util import find_spec

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
    
    # Get database URL and convert to a driver that is actually installed
    _db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres.lkvstjspyeslqzzjmyca:Group_7@aws-1-eu-central-1.pooler.supabase.com:5432/postgres")

    # Supabase recommends psycopg3, but fall back to psycopg2 if psycopg is missing
    if _db_url.startswith("postgresql://"):
        driver = "psycopg" if find_spec("psycopg") else "psycopg2"
        _db_url = _db_url.replace("postgresql://", f"postgresql+{driver}://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    # Connection pool settings to handle Supabase connection issues
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": 15,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
    }
