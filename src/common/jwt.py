"""
JWT helpers mirroring the NestJS `@nestjs/jwt` behavior.

- Access & refresh tokens are HS256, signed with SEPARATE secrets.
- Claims: {sub, email, role, clubId} (+ iat/exp). `clubId` is OMITTED when
  null, exactly as `jsonwebtoken` drops undefined values (super admins).
- Durations use NestJS strings like "30d" / "60d" / "15m".
- Two special 15-minute tokens (signed with the ACCESS secret):
    * first-login reset  → claim {requiresPasswordReset: true}
    * password reset     → claim {isPasswordReset: true}
- Response keys are `access_token` / `refresh_token` (NOT access/refresh).
"""
import re
import time

import jwt
from django.conf import settings

_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def duration_to_seconds(value) -> int:
    """Convert "30d"/"60d"/"15m"/"3600" to seconds."""
    if isinstance(value, (int, float)):
        return int(value)
    value = str(value).strip()
    match = re.fullmatch(r"(\d+)([smhd])", value)
    if match:
        return int(match.group(1)) * _UNIT_SECONDS[match.group(2)]
    return int(value)  # bare number of seconds


def _sign(claims: dict, secret: str, expires_in) -> str:
    now = int(time.time())
    payload = dict(claims)
    payload["iat"] = now
    payload["exp"] = now + duration_to_seconds(expires_in)
    return jwt.encode(payload, secret, algorithm="HS256")


def _base_claims(user_id: str, email: str, role: str, club_id):
    claims = {"sub": str(user_id), "email": email, "role": role}
    # Omit clubId when absent — matches jsonwebtoken dropping `undefined`.
    if club_id is not None:
        claims["clubId"] = str(club_id)
    return claims


def generate_tokens(user_id: str, email: str, role: str, club_id=None) -> dict:
    claims = _base_claims(user_id, email, role, club_id)
    return {
        "access_token": _sign(
            claims, settings.JWT_ACCESS_SECRET, settings.JWT_ACCESS_EXPIRES_IN
        ),
        "refresh_token": _sign(
            claims, settings.JWT_REFRESH_SECRET, settings.JWT_REFRESH_EXPIRES_IN
        ),
    }


def sign_first_login_reset_token(user_id: str, email: str) -> str:
    return _sign(
        {"sub": str(user_id), "email": email, "requiresPasswordReset": True},
        settings.JWT_ACCESS_SECRET,
        "15m",
    )


def sign_password_reset_token(user_id: str, email: str) -> str:
    return _sign(
        {"sub": str(user_id), "email": email, "isPasswordReset": True},
        settings.JWT_ACCESS_SECRET,
        "15m",
    )


def verify(token: str, secret: str) -> dict:
    """Decode & verify; raises jwt.PyJWTError on failure."""
    return jwt.decode(token, secret, algorithms=["HS256"])


def verify_access(token: str) -> dict:
    return verify(token, settings.JWT_ACCESS_SECRET)


def verify_refresh(token: str) -> dict:
    return verify(token, settings.JWT_REFRESH_SECRET)
