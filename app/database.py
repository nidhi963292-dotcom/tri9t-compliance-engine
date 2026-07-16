# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Local SQLite engine configuration setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)