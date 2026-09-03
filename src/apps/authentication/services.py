"""
AuthService — port of `src/auth/auth.service.ts`.

NOTE (source-vs-doc): `reset_first_login_password` and `reset_password` wrap
their whole body in a try/except that rethrows ANY internal error as a single
`401 "Invalid or expired reset token"`. So a wrong-token-type returns 401, not
the 400 the per-module docs claim. This matches the NestJS SOURCE (the oracle).
"""
from apps.users import services as users_service
from apps.users.serializers import embed_auth_user
from common import jwt as jwt_helper
from common.hashing import verify_password
from common.exceptions import Unauthorized, Forbidden, BadRequest


def login(email, password):
    user = users_service.find_by_email(email)
    if not user:
        raise Unauthorized("Invalid credentials")
    if not verify_password(password, user.password):
        raise Unauthorized("Invalid credentials")

    if user.is_first_login:
        reset_token = jwt_helper.sign_first_login_reset_token(user.id, user.email)
        # Custom-object 403 body (no statusCode/error keys), matching NestJS.
        raise Forbidden(
            {
                "message": "Password reset required on first login",
                "requiresPasswordReset": True,
                "resetToken": reset_token,
            }
        )

    tokens = jwt_helper.generate_tokens(
        user.id, user.email, user.role, user.club_id_id
    )
    return {**tokens, "user": embed_auth_user(user, club_populated=False)}


def reset_first_login_password(reset_token, new_password):
    try:
        payload = jwt_helper.verify_access(reset_token)
        if not payload.get("requiresPasswordReset"):
            raise BadRequest("Invalid reset token type")
        updated = users_service.update_password(payload.get("sub"), new_password)
        if not updated:
            raise Unauthorized("User not found")
        tokens = jwt_helper.generate_tokens(
            updated.id, updated.email, updated.role, updated.club_id_id
        )
        return {**tokens, "user": embed_auth_user(updated, club_populated=False)}
    except Exception:
        # COMPATIBILITY: NestJS swallows ALL errors here into this single 401.
        raise Unauthorized("Invalid or expired reset token")


def refresh_tokens(refresh_token):
    try:
        payload = jwt_helper.verify_refresh(refresh_token)
        user = users_service.find_by_id(payload.get("sub"))
        if not user:
            raise Unauthorized("User no longer exists")
        tokens = jwt_helper.generate_tokens(
            user.id, user.email, user.role, user.club_id_id
        )
        # refresh POPULATES clubId → embedded user gets {_id, name}.
        return {**tokens, "user": embed_auth_user(user, club_populated=True)}
    except Exception:
        raise Unauthorized("Invalid or expired refresh token")


def forgot_password(email):
    user = users_service.find_by_email(email)
    generic = {"message": "If the email is registered, a reset code has been sent"}
    if not user:
        # Anti-enumeration: identical response, no email sent.
        return generic
    token = jwt_helper.sign_password_reset_token(user.id, user.email)
    from common.mail import send_password_reset_email

    send_password_reset_email(user.email, token)
    return generic


def reset_password(token, new_password):
    try:
        payload = jwt_helper.verify_access(token)
        if not payload.get("isPasswordReset"):
            raise BadRequest("Invalid reset token type")
        updated = users_service.update_password(payload.get("sub"), new_password)
        if not updated:
            raise Unauthorized("User not found")
        return {"message": "Password has been reset successfully"}
    except Exception:
        # COMPATIBILITY: NestJS swallows ALL errors here into this single 401.
        raise Unauthorized("Invalid or expired reset token")


def change_password(email, old_password, new_password):
    user = users_service.find_by_email(email)
    if not user:
        raise Unauthorized("User not found")
    if not verify_password(old_password, user.password):
        raise BadRequest("Incorrect old password")
    users_service.update_password(user.id, new_password)
    return {"message": "Password changed successfully"}
