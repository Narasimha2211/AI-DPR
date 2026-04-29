# ============================================
# PostgreSQL Configuration
# ============================================

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.postgres_models import Base

# PostgreSQL connection string
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:@localhost:5432/dpr_db"
)

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables
def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ PostgreSQL tables created successfully")

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
