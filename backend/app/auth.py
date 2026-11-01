"""Autenticação por JWT do Supabase.

T1.2: validação do JWT e dependência `get_current_user`.

O Supabase assina os tokens de duas formas, e ambas são aceites:
- ES256/RS256 (chaves assimétricas): a chave pública vem do JWKS do projeto.
- HS256 (segredo partilhado): usa `SUPABASE_JWT_SECRET`.
O algoritmo do cabeçalho só escolhe a fonte da chave; nunca se verifica um token HS256
com uma chave pública.
"""

import logging
import re
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()

_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}

# O `sub` entra em caminhos do Storage e em chaves do Redis: só caracteres seguros.
USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

SHARED_SECRET_ALGORITHM = "HS256"  # noqa: S105 - nome do algoritmo, não um segredo
JWKS_ALGORITHMS = ("ES256", "RS256")
JWKS_CACHE_LIFESPAN_S = 600
JWKS_TIMEOUT_S = 10
CLOCK_SKEW_LEEWAY_S = 30
REQUIRED_CLAIMS = ["exp", "sub", "aud", "iss"]


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers=_UNAUTHORIZED_HEADERS,
    )


def _expected_issuer() -> str:
    return settings.SUPABASE_JWT_ISSUER or f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1"


@lru_cache(maxsize=1)
def _jwks_client() -> jwt.PyJWKClient:
    """Cliente JWKS partilhado; guarda as chaves em cache entre pedidos."""
    return jwt.PyJWKClient(
        f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json",
        cache_keys=True,
        lifespan=JWKS_CACHE_LIFESPAN_S,
        timeout=JWKS_TIMEOUT_S,
    )


def _signing_key(token: str, algorithm: str) -> Any:
    """Escolhe a chave de verificação conforme o algoritmo declarado no cabeçalho."""
    if algorithm == SHARED_SECRET_ALGORITHM:
        if not settings.SUPABASE_JWT_SECRET:
            raise _unauthorized("Unsupported token algorithm")
        return settings.SUPABASE_JWT_SECRET
    if algorithm in JWKS_ALGORITHMS:
        return _jwks_client().get_signing_key_from_jwt(token).key
    raise _unauthorized("Unsupported token algorithm")


def verify_supabase_jwt(token: str) -> dict[str, Any]:
    """Valida um JWT do Supabase e devolve o seu conteúdo.

    Verifica a assinatura, a expiração, o `aud` e o `iss`, e exige `sub`.

    Args:
        token: JWT recebido no cabeçalho Authorization.

    Returns:
        Conteúdo (claims) do token.

    Raises:
        HTTPException: 401 se o token for inválido ou expirado; 503 se o JWKS
            não puder ser obtido.
    """
    try:
        algorithm = jwt.get_unverified_header(token).get("alg", "")
        payload: dict[str, Any] = jwt.decode(
            token,
            _signing_key(token, algorithm),
            algorithms=[algorithm],
            audience=settings.SUPABASE_JWT_AUDIENCE,
            issuer=_expected_issuer(),
            leeway=CLOCK_SKEW_LEEWAY_S,
            options={"require": REQUIRED_CLAIMS},
        )
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Token has expired") from exc
    except jwt.PyJWKClientConnectionError as exc:
        logger.error("Could not fetch the Supabase JWKS: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        ) from exc
    except jwt.PyJWTError as exc:
        logger.info("JWT rejeitado: %s", type(exc).__name__)
        raise _unauthorized("Could not validate credentials") from exc
    return payload


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict[str, Any]:
    """Devolve o utilizador autenticado a partir do JWT do pedido.

    A verificação corre numa thread porque a primeira consulta ao JWKS é bloqueante.

    Args:
        credentials: Credenciais Bearer extraídas do pedido.

    Returns:
        Claims do token validado.

    Raises:
        HTTPException: 401 se a autenticação falhar.
    """
    claims: dict[str, Any] = await run_in_threadpool(verify_supabase_jwt, credentials.credentials)
    return claims


async def get_current_user_id(
    claims: Annotated[dict[str, Any], Depends(get_current_user)],
) -> str:
    """Devolve o identificador do utilizador autenticado (`sub`), já validado.

    Args:
        claims: Claims do token validado.

    Returns:
        O `sub` do token.

    Raises:
        HTTPException: 401 se o `sub` tiver caracteres não permitidos.
    """
    user_id = str(claims.get("sub", ""))
    if not USER_ID_PATTERN.fullmatch(user_id):
        raise _unauthorized("Invalid token: bad subject")
    return user_id


CurrentUserId = Annotated[str, Depends(get_current_user_id)]
