"""Application configuration using Pydantic Settings
T1.1: Backend base: FastAPI, config Pydantic, logging, CORS, `/health`
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = "City Planner Geo"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    BACKEND_CORS_ORIGINS: list = ["*"]

    # Database (Supabase)
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_PUBLISHABLE_KEY: str = Field(..., env="SUPABASE_PUBLISHABLE_KEY")
    SUPABASE_SECRET_KEY: str = Field(..., env="SUPABASE_SECRET_KEY")

    # Redis (for Celery)
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # DGT - Regime Florestal (ArcGIS REST FeatureServer, layer 1562)
    DGT_REGIME_FLORESTAL_URL: str = Field(
        default=(
            "https://infogeo.dgterritorio.gov.pt/arcgis/rest/services/Hosted/"
            "Regime_florestal/FeatureServer/1562"
        ),
        env="DGT_REGIME_FLORESTAL_URL",
    )

    # GBIF
    GBIF_USER_AGENT: str = Field(
        default="city-planner-geo/0.1.0 (https://github.com/city-planner-geo)",
        env="GBIF_USER_AGENT",
    )

    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create settings instance
settings = Settings()
