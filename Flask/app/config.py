import os

class Config:
    SECRET_KEY = 'a3b7c0f9c61a497e8f6d43b295de0f5dfd0a54e7d601e802d94ec32d58b99b8d'
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI", 
        "postgresql://postgres:Group_7@db.lkvstjspyeslqzzjmyca.supabase.co:5432/postgres"
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False