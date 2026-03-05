# ============================================
# AI DPR Analysis System - Main Application
# ============================================
# AI-Powered Detailed Project Report Analysis
# for Indian Government Projects
# ============================================

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from loguru import logger

from config.settings import settings, BASE_DIR
from app.models.database import init_db
from app.api.routes import upload, analysis, scoring, risk, dashboard, learning


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    logger.info("=" * 60)
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📋 AI DPR Analysis System – PostgreSQL backed")
    logger.info("=" * 60)

    # Initialize database (create tables if not exist)
    await init_db()
    logger.info("✅ PostgreSQL database initialized")

    # Seed reference data on first run
    from app.services.seed import seed_reference_data
    await seed_reference_data()
    logger.info("✅ Reference data verified / seeded")

    yield

    # Shutdown
    logger.info("🛑 Shutting down AI DPR Analysis System")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
frontend_path = BASE_DIR / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# Register API routers
app.include_router(upload.router)
app.include_router(analysis.router)
app.include_router(scoring.router)
app.include_router(risk.router)
app.include_router(dashboard.router)
app.include_router(learning.router)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend dashboard."""
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse(content="""
    <html>
        <head><title>AI DPR Analysis System</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px; background: #0f172a; color: white;">
            <h1>🏛️ AI DPR Analysis System</h1>
            <p>AI-Powered Detailed Project Report Analysis for Indian Government Projects</p>
            <br>
            <a href="/docs" style="color: #60a5fa; font-size: 18px;">📖 API Documentation</a>
            <br><br>
            <a href="/redoc" style="color: #60a5fa; font-size: 18px;">📚 ReDoc</a>
        </body>
    </html>
    """)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from datetime import datetime
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }


# Run with: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
