"""Autenticação por JWT do Supabase.

T1.2: validação do JWT e dependência `get_current_user`.
"""

import logging
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()

_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers=_UNAUTHORIZED_HEADERS,
    )


def verify_supabase_jwt(token: str) -> dict[str, Any]:
    """Valida um JWT e devolve o seu conteúdo.

    A assinatura é verificada com `SECRET_KEY` (HS256). A passagem para JWKS
    fica para a decisão pendente da T1.2.

    Args:
        token: JWT recebido no cabeçalho Authorization.

    Returns:
        Conteúdo (claims) do token.

    Raises:
        HTTPException: 401 se o token for inválido, expirado ou sem `sub`.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": True},
        )
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        logger.info("JWT rejeitado: %s", type(exc).__name__)
        raise _unauthorized("Could not validate credentials") from exc

    if "sub" not in payload:
        raise _unauthorized("Invalid token: missing subject")
    return payload


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict[str, Any]:
    """Devolve o utilizador autenticado a partir do JWT do pedido.

    Args:
        credentials: Credenciais Bearer extraídas do pedido.

    Returns:
        Claims do token validado.

    Raises:
        HTTPException: 401 se a autenticação falhar.
    """
    return verify_supabase_jwt(credentials.credentials)
