"""
DRF authentication mirroring the NestJS JwtStrategy.

It verifies the Bearer ACCESS token and exposes a lightweight principal on
`request.user` carrying the same claim shape NestJS puts on `req.user`:
    {userId, email, role, clubId}

We intentionally do NOT load the DB user here (NestJS authorizes off the token
claims). Services that need the row load it by `user_id`.
"""
import jwt
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from . import jwt as jwt_helper


class JwtPrincipal:
    """Mirror of NestJS `req.user`."""

    is_authenticated = True

    def __init__(self, user_id, email, role, club_id):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.club_id = club_id

    def __str__(self):
        return f"JwtPrincipal<{self.user_id} {self.role}>"


class JWTAccessAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None  # no credentials → DRF treats as unauthenticated
        token = header[len("Bearer "):].strip()
        try:
            payload = jwt_helper.verify_access(token)
        except jwt.PyJWTError:
            # NestJS returns 401 "Unauthorized" for an invalid/expired token.
            raise AuthenticationFailed("Unauthorized")

        principal = JwtPrincipal(
            user_id=payload.get("sub"),
            email=payload.get("email"),
            role=payload.get("role"),
            club_id=payload.get("clubId"),
        )
        return (principal, token)

    def authenticate_header(self, request):
        # Presence of this makes DRF return 401 (not 403) for missing auth.
        return "Bearer"
