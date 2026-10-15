import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import logging
from backend.config import APP_NAME, APP_VERSION, FRONTEND_DIR, validate_production_config, IS_VERCEL
from backend.database import init_db
from backend.routers import auth, uploads, transactions, analytics, budgets, reports, settings

logger = logging.getLogger("spendsense")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate production configuration if running in production
    config_errors = validate_production_config()
    if config_errors:
        for err in config_errors:
            logger.error(f"[CONFIG ERROR] {err}")
    # Initialize SQLite database and seed defaults idempotently on startup
    init_db()
    if IS_VERCEL:
        try:
            from backend.data_generator import generate_demo_dataset
            from backend.database import get_db
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM transactions WHERE user_id = 1;")
                count = cursor.fetchone()[0]
                if count == 0:
                    generate_demo_dataset(user_id=1)
        except Exception as e:
            logger.warning(f"Auto-seed on Vercel: {e}")
    yield

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="SpendSense Personal Spending Behavior Analyzer API",
    lifespan=lifespan
)

# CORS configuration for frontend communication with cookies/credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:3000", "http://127.0.0.1:5500"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(uploads.router)
app.include_router(transactions.router)
app.include_router(analytics.router)
app.include_router(budgets.router)
app.include_router(reports.router)
app.include_router(settings.router)

# Health Check
@app.get("/api/health", tags=["Health"])
async def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "app": APP_NAME,
        "version": APP_VERSION
    }

# Mount Frontend static files for seamless single-server full-stack experience
if FRONTEND_DIR.exists():
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
    if (FRONTEND_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    # Serve HTML pages directly
    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{page_name}.html", include_in_schema=False)
    async def serve_html(page_name: str):
        page_file = FRONTEND_DIR / f"{page_name}.html"
        if page_file.exists():
            return FileResponse(page_file)
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{page_name}", include_in_schema=False)
    async def serve_html_without_ext(page_name: str):
        page_file = FRONTEND_DIR / f"{page_name}.html"
        if page_file.exists():
            return FileResponse(page_file)
        direct_file = FRONTEND_DIR / page_name
        if direct_file.is_file():
            return FileResponse(direct_file)
        return FileResponse(FRONTEND_DIR / "index.html")
