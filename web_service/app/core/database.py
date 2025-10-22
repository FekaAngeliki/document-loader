"""
Basic database initialization (mock for local development)
"""
import structlog

logger = structlog.get_logger(__name__)

async def init_db():
    """Initialize database connections"""
    logger.info("Database initialization skipped for local development")
    return True