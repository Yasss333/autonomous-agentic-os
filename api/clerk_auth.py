from functools import lru_cache
from urllib.parse import urlsplit

import jwt
from fastapi import HTTPException

from . import config


@lru_cache(maxsize=1)
def _jwks(issuer: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json", timeout=5)


def verify_session(authorization: str) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token or len(token) > 8192:
        raise HTTPException(401, "Clerk session required", headers={"WWW-Authenticate": "Bearer"})

    issuer = urlsplit(config.CLERK_ISSUER)
    if (issuer.scheme != "https" or not issuer.hostname or issuer.username is not None
            or issuer.path or issuer.query or issuer.fragment or not config.CLERK_AUTHORIZED_PARTIES):
        raise HTTPException(503, "Clerk authentication is not configured")

    # Clerk's instance JWKS verifies short-lived session tokens without a secret API key.
    # https://clerk.com/docs/guides/sessions/manual-jwt-verification
    try:
        if jwt.get_unverified_header(token).get("alg") != "RS256":
            raise jwt.InvalidTokenError()
        key = _jwks(config.CLERK_ISSUER).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, key, algorithms=["RS256"], issuer=config.CLERK_ISSUER,
            leeway=10,  # Allow the measured local clock skew without disabling time checks.
            options={"require": ["iss", "sub", "sid", "exp", "nbf", "iat", "azp"]},
        )
        azp, sid = claims["azp"], claims["sid"]
        if (not isinstance(azp, str) or azp not in config.CLERK_AUTHORIZED_PARTIES
                or not isinstance(sid, str) or not sid.startswith("sess_")
                or not claims["sub"].startswith("user_") or claims.get("sts") not in (None, "active")):
            raise jwt.InvalidTokenError()
        return claims["sub"]
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(503, "Clerk token verification is unavailable") from None
    except (jwt.PyJWTError, TypeError, ValueError, OverflowError):
        raise HTTPException(401, "Invalid Clerk session", headers={"WWW-Authenticate": "Bearer"}) from None
