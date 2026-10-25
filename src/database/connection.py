"""
Database Connection & Session Management
Supports SQLite (local default) and PostgreSQL (production).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Default to SQLite in ./data/nikom_tenders.db for instant portability
DEFAULT_DB_URL = "sqlite:///./data/nikom_tenders.db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

# SQLite requires check_same_thread=False for multithreading
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    os.makedirs("./data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
