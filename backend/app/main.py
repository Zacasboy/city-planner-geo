"""
City Planner Geo - Main FastAPI Application
T1.1: Backend base: FastAPI, config Pydantic, logging, CORS, `/health`
"""

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import settings and routers
from app.config import settings
# from app.api import geo, ecology, forest, structural, materials, reports
# from app.tasks import analysis

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        # logging.FileHandler("app.log")  # Uncomment for file logging
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Sistema de Planeamento de Cidades Geolocalizadas - API",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint to verify the API is running.
    Returns 200 OK if the service is healthy.
    """
    logger.info("Health check endpoint accessed")
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint with basic API information.
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }

# Include routers (uncomment as routers are implemented)
# app.include_router(geo.router, prefix="/geo", tags=["geo"])
# app.include_router(ecology.router, prefix="/ecology", tags=["ecology"])
# app.include_router(forest.router, prefix="/forest", tags=["forest"])
# app.include_router(structural.router, prefix="/structural", tags=["structural"])
# app.include_router(materials.router, prefix="/materials", tags=["materials"])
# app.include_router(reports.router, prefix="/reports", tags=["reports"])
# app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME}...")
    logger.info(f"Environment: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.APP_NAME}...")