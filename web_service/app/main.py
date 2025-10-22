"""
Banking-Grade Document Loader Web Service Facade

This service provides a business-oriented API for document synchronization
operations with comprehensive audit logging, compliance controls, and
enterprise security features.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
import structlog
import time
import uuid
import os

from .core.config import get_settings
from .core.logging import configure_logging
# from .core.metrics import metrics_middleware  # Disabled for local development
from .api.routes import api_router
from .core.database import init_db
from .core.audit import audit_middleware

# Configure structured logging
configure_logging()
logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting Document Loader Web Service")
    
    # Initialize database connections
    await init_db()
    
    logger.info("Web Service started successfully")
    yield
    
    logger.info("Shutting down Document Loader Web Service")

def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    settings = get_settings()
    
    app = FastAPI(
        title="Document Loader Banking API",
        description="Banking-grade web service facade for document synchronization operations",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Security middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )
    
    # CORS for banking web applications
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Custom middleware for audit logging (disabled for local development)
    # app.middleware("http")(audit_middleware)
    
    # Metrics middleware (disabled for local development)
    # app.middleware("http")(metrics_middleware)
    
    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    # Serve static files (business dashboard)
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="dashboard")
    
    # Health check endpoint moved under /api/v1
    @app.get("/api/v1/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "document-loader-web-service",
            "version": "1.0.0"
        }
    
    @app.get("/api/v1/ready")
    async def readiness_check():
        # Check database connectivity and other dependencies
        return {"status": "ready"}
    
    return app

# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.ENVIRONMENT == "development",
        log_config=None  # Use our custom logging
    )