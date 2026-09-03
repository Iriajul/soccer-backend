"""
Users request DTOs (validation) and response presenters (exact JSON shapes).

The response shapes intentionally differ per endpoint, mirroring Mongoose:
  * embedded auth user  → keys {id, name, email, role, profileImage, clubId}
  * GET /users/me       → full doc, clubId POPULATED {_id,name}, +context, no __v
  * PATCH /users/me     → full doc, clubId RAW string, includes __v
  * GET /users list     → full docs, clubId RAW string, includes __v
Do not unify these — the differences are part of the contract.
"""
from rest_framework import serializers

from common.roles import UserRole
from common.utils import iso_z


# ── Request DTOs ─────────────────────────────────────────────────────────────
class InviteUserSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=[r.value for r in UserRole])
    clubId = serializers.CharField(required=False, allow_null=True)


class UpdateProfileSerializer(serializers.Serializer):
    # All optional; unknown fields are ignored (matches ValidationPipe whitelist).
    name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(required=False)


class UpdateRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[r.value for r in UserRole])


# ── Response presenters ───────────────────────────────────────────────────────
def embed_auth_user(user, club_populated=False):
    """
    The user object embedded in login / first-login-reset / refresh responses.
    Key is `id` (NOT `_id`). `clubId` is a raw string on login/first-login and
    a populated {_id, name} object on refresh. It is OMITTED entirely when the
    user has no club (super admin) — matching JS dropping an undefined clubId.
    """
    data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "profileImage": user.profile_image or None,
    }
    if user.club_id_id is not None:
        if club_populated:
            data["clubId"] = {"_id": user.club_id_id, "name": user.club_id.name}
        else:
            data["clubId"] = user.club_id_id
    return data


def _full_common(user):
    return {
        "_id": user.id,
        "name": user.name,
        "email": user.email,
        "profileImage": user.profile_image or None,
        "role": user.role,
        "isFirstLogin": user.is_first_login,
        "childPlayerIds": [str(x) for x in (user.child_player_ids or [])],
        "parentIds": [str(x) for x in (user.parent_ids or [])],
        "createdAt": iso_z(user.created_at),
        "updatedAt": iso_z(user.updated_at),
    }


def list_user_dict(user):
    """GET /users item: full doc, clubId RAW string, includes __v (Mongoose)."""
    data = _full_common(user)
    data["clubId"] = user.club_id_id
    data["__v"] = 0
    return data


def updated_profile_dict(user):
    """PATCH /users/me: full doc, clubId RAW string, includes __v, no context."""
    data = _full_common(user)
    data["clubId"] = user.club_id_id
    data["__v"] = 0
    return data


def profile_with_context_dict(user, context):
    """
    GET /users/me: full doc via .lean() with clubId POPULATED and `context`
    appended. NestJS excludes __v here (`.select('-password -__v')`).
    """
    data = _full_common(user)
    if user.club_id_id is not None:
        data["clubId"] = {"_id": user.club_id_id, "name": user.club_id.name}
    else:
        data["clubId"] = None
    # GET /users/me uses .lean() → NO toJSON transform → profileImage is
    # ABSENT when unset (unlike list/patch, which are non-lean → null).
    if data.get("profileImage") is None:
        data.pop("profileImage", None)
    data["context"] = context
    return data
