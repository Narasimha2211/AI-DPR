# ============================================
# Database Compatibility Layer (PostgreSQL)
# ============================================
# This file provides backward-compatible imports
# for existing code that references database.py.
# Actual database operations use PostgreSQL via
# config/postgres_config.py
# ============================================


async def get_db():
    """Compatibility stub – routes that still use Depends(get_db)."""
    yield None


async def init_db():
    """No-op: PostgreSQL tables are created on startup."""
    pass
