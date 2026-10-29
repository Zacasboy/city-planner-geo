"""Supabase JWT Authentication
T1.2: Autenticação: validação JWT Supabase, dependency `get_current_user`
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.config import settings

# HTTP Bearer token scheme
security = HTTPBearer()


def verify_supabase_jwt(token: str) -> dict:
    """Verify Supabase JWT token and return user payload.

    Args:
        token: JWT token string

    Returns:
        dict: Decoded token payload with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Decode and verify the JWT
        # Supabase uses HS256 algorithm with the JWT secret
        # Note: In production, you should verify the signature using Supabase's JWKS
        # For development, we're using the secret key approach

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": True},
        )

        # Additional validation: check if token is from Supabase
        # Supabase tokens typically have 'aud' claim or specific issuer
        # For now, we'll validate basic structure

        # Check required fields
        if "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check token expiration (already handled by jwt.decode with verify_exp=True)
        # Additional checks can be added here if needed

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency to get the current authenticated user from Supabase JWT.

    This function will be used in path dependencies like:
    @app.get("/protected")
    async def protected_route(current_user: dict = Depends(get_current_user)):
        ...

    Args:
        credentials: HTTP Authorization credentials from the request

    Returns:
        dict: User information from the validated JWT token

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    user = verify_supabase_jwt(token)
    return user


# Optional: Alternative implementation using Supabase's JWKS for production
# This is more secure but requires fetching JWKS from Supabase
"""
import requests
import json

def get_supabase_jwks():
    '''Fetch Supabase JWKS for token verification'''
    jwks_url = f"{settings.SUPABASE_URL}/.well-known/jwks.json"
    response = requests.get(jwks_url)
    response.raise_for_status()
    return response.json()

def verify_supabase_jwt_production(token: str) -> dict:
    '''Verify JWT using Supabase JWKS (more secure for production)'''
    # Implementation would involve:
    # 1. Fetch JWKS from Supabase
    # 2. Extract key from token header
    # 3. Verify signature using the appropriate key
    # 4. Validate claims
    pass
"""
