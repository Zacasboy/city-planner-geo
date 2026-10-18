"""
City Planner Geo - Main FastAPI Application
T1.1: Backend base: FastAPI, config Pydantic, logging, CORS, `/health`
"""

import logging
import sys
import uuid
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

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
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json"
)

# Add request ID middleware for tracing
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Process time: {process_time:.3f}s - "
        f"Request ID: {getattr(request.state, 'request_id', 'N/A')}"
    )
    return response

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure trusted hosts (for production)
# app.add_middleware(
#     TrustedHostMiddleware,
#     allowed_hosts=["example.com", "*.example.com"]
# )

# Global exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP {exc.status_code}: {exc.detail} - Request ID: {getattr(request.state, 'request_id', 'N/A')}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc.errors()} - Request ID: {getattr(request.state, 'request_id', 'N/A')}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "message": "Validation error",
                "details": exc.errors(),
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)} - Request ID: {getattr(request.state, 'request_id', 'N/A')}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "request_id": getattr(request.state, 'request_id', None)
            }
        }
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
        "version": settings.APP_VERSION,
        "timestamp": datetime.now().isoformat(),
        "environment": "DEBUG" if settings.DEBUG else "PRODUCTION"
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
        "health": "/health",
        "api_v1": "/api/v1"
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
    logger.info(f"Debug mode: {settings.DEBUG}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.APP_NAME}...")