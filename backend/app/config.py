"""Configuração da aplicação (Pydantic Settings).

T1.1: base do backend com FastAPI, configuração, logging, CORS e `/health`.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CORS_ORIGINS = ["http://localhost:8501"]
DEFAULT_DGT_REGIME_FLORESTAL_URL = (
    "https://infogeo.dgterritorio.gov.pt/arcgis/rest/services/Hosted/"
    "Regime_florestal/FeatureServer/1562"
)
DEFAULT_GBIF_USER_AGENT = "city-planner-geo/0.1.0 (https://github.com/city-planner-geo)"


class Settings(BaseSettings):
    """Definições da aplicação, lidas de variáveis de ambiente e de `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        # O `.env.example` tem chaves que ainda não são campos (HF_TOKEN, ...).
        extra="ignore",
    )

    APP_NAME: str = "City Planner Geo"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Por omissão só escuta localmente; em contentores definir HOST explicitamente.
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Lista JSON, por exemplo '["https://app.exemplo.pt"]'.
    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=lambda: list(DEFAULT_CORS_ORIGINS))

    SUPABASE_URL: str
    SUPABASE_PUBLISHABLE_KEY: str
    SUPABASE_SECRET_KEY: str

    REDIS_URL: str = "redis://localhost:6379/0"

    DGT_REGIME_FLORESTAL_URL: str = DEFAULT_DGT_REGIME_FLORESTAL_URL
    GBIF_USER_AGENT: str = DEFAULT_GBIF_USER_AGENT

    # Validação dos JWT do Supabase (ver backend/app/auth.py).
    # Com chaves assimétricas (ES256/RS256) usa-se o JWKS do projeto e este segredo não é preciso.
    SUPABASE_JWT_SECRET: str = ""  # só para projetos com segredo partilhado (HS256)
    SUPABASE_JWT_AUDIENCE: str = "authenticated"
    SUPABASE_JWT_ISSUER: str = ""  # vazio = "<SUPABASE_URL>/auth/v1"

    LOG_LEVEL: str = "INFO"

    # Observabilidade (T0.6). Sem DSN o Sentry fica desligado.
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = ""  # vazio = "development" ou "production" conforme DEBUG
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("BACKEND_CORS_ORIGINS")
    @classmethod
    def _reject_wildcard_origin(cls, origins: list[str]) -> list[str]:
        """Impede `*`, porque a API responde com credenciais (cookies/Authorization)."""
        if "*" in origins:
            msg = "BACKEND_CORS_ORIGINS não pode conter '*' (a API usa credenciais)"
            raise ValueError(msg)
        return origins


settings = Settings()
