import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
    
    # Get database URL and convert to use psycopg3 driver if needed
    _db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres.lkvstjspyeslqzzjmyca:Group_7@aws-1-eu-central-1.pooler.supabase.com:5432/postgres")
    
    #Convert postgresql:// to postgresql+psycopg:// to use psycopg3 
    if _db_url.startswith("postgresql://") and not _db_url.startswith("postgresql+psycopg://"):
        _db_url = _db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    # Connection pool settings to handle Supabase connection issues
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": 15,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
    }