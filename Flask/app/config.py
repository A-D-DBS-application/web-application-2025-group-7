import os

class Config:
    SECRET_KEY = 'a3b7c0f9c61a497e8f6d43b295de0f5dfd0a54e7d601e802d94ec32d58b99b8d'

    # probeer eerst environment variable DATABASE_URL, anders gebruik SQLite lokaal
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///database.db'
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False