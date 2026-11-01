"""Aplicação FastAPI principal.

T1.1: base do backend com FastAPI, configuração, logging, CORS e `/health`.
"""

import logging
import sys
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api import morphology, reports
from backend.app.auth import get_current_user, get_current_user_id
from backend.app.config import settings
from backend.app.services.ecology_service import router as ecology_router
from backend.app.services.forest_service import router as forest_router
from backend.app.services.geo_service import router as geo_router
from backend.app.services.orchestration_service import router as orchestration_router
from backend.app.services.structural_service import router as structural_router

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

UNKNOWN_REQUEST_ID = "N/A"


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Regista o arranque e o encerramento da aplicação."""
    logger.info("Starting %s...", settings.APP_NAME)
    logger.info("Environment: %s", "DEBUG" if settings.DEBUG else "PRODUCTION")
    yield
    logger.info("Shutting down %s...", settings.APP_NAME)


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Sistema de Planeamento de Cidades Geolocalizadas - API",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_request_id(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Associa um identificador único a cada pedido, para rastreio."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Regista método, caminho, estado e duração de cada pedido."""
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Process time: {process_time:.3f}s - "
        f"Request ID: {_request_id(request) or UNKNOWN_REQUEST_ID}"
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Devolve erros HTTP no formato `{"error": {...}}`."""
    logger.error(
        "HTTP %s: %s - Request ID: %s",
        exc.status_code,
        exc.detail,
        _request_id(request) or UNKNOWN_REQUEST_ID,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "request_id": _request_id(request),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Devolve erros de validação no formato `{"error": {...}}`."""
    logger.error(
        "Validation error: %s - Request ID: %s",
        exc.errors(),
        _request_id(request) or UNKNOWN_REQUEST_ID,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": {
                "code": status.HTTP_422_UNPROCESSABLE_CONTENT,
                "message": "Validation error",
                "details": exc.errors(),
                "request_id": _request_id(request),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Esconde detalhes internos de erros não tratados."""
    logger.error(
        "Unhandled exception: %s - Request ID: %s",
        exc,
        _request_id(request) or UNKNOWN_REQUEST_ID,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "request_id": _request_id(request),
            }
        },
    )


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Verifica se a API está a responder."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now().isoformat(),
        "environment": "DEBUG" if settings.DEBUG else "PRODUCTION",
    }


# Root endpoint
@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Devolve informação básica da API."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "api_v1": "/api/v1",
    }


PROTECTED = [Depends(get_current_user_id)]

app.include_router(geo_router, prefix="/geo", tags=["geo"], dependencies=PROTECTED)
app.include_router(ecology_router, prefix="/ecology", tags=["ecology"], dependencies=PROTECTED)
app.include_router(forest_router, prefix="/forest", tags=["forest"], dependencies=PROTECTED)
app.include_router(
    structural_router, prefix="/structural", tags=["structural"], dependencies=PROTECTED
)
app.include_router(morphology.router)
app.include_router(reports.router)
app.include_router(orchestration_router, prefix="/orchestration", tags=["orchestration"])


@app.get("/protected", tags=["auth"])
async def protected_route(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    """Rota de exemplo protegida por JWT; devolve o utilizador do token."""
    return {
        "message": f"Hello, {current_user.get('email', 'user')}!",
        "user_id": current_user.get("sub"),
        "authenticated": True,
    }
