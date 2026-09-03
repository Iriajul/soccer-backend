"""
UsersService — port of `src/users/users.service.ts`.

Authorization (hierarchy + club isolation) lives here, exactly as in NestJS,
not in serializers. Error messages/status codes are reproduced verbatim,
including the 409-not-404 quirk on role update.
"""
import math
import random
import string
import logging

from django.conf import settings
from django.db import transaction

from apps.clubs.models import Club
from apps.teams.models import Team
from common.roles import UserRole, weight, outranks, subordinate_roles
from common.hashing import hash_password
from common.tenancy import cast_object_id_or_500
from common.exceptions import Forbidden, Conflict, NotFound, InternalServerError
from .models import User
from .serializers import list_user_dict, updated_profile_dict, profile_with_context_dict

logger = logging.getLogger(__name__)


def _is_dev():
    return getattr(settings, "NODE_ENV", "development") != "production"


def find_by_email(email):
    return User.objects.filter(email=email).first()


def find_by_id(user_id):
    return User.objects.filter(id=user_id).first()


def update_password(user_id, raw_new_password):
    """Set a new password and clear the first-login flag; returns the user."""
    user = User.objects.filter(id=user_id).first()
    if not user:
        return None
    user.password = hash_password(raw_new_password)
    user.is_first_login = False
    user.save(update_fields=["password", "is_first_login", "updated_at"])
    return user


def invite_staff_member(dto, inviter=None):
    """
    Create a user with a temporary password and email/console the invite.
    Wrapped in a transaction: a failed prod email rolls back the user, matching
    NestJS. `inviter` is the JWT principal (None when called by club creation,
    which skips the hierarchy/club-isolation checks).
    """
    club_id = dto.get("clubId")
    try:
        with transaction.atomic():
            if inviter is not None:
                if not outranks(inviter.role, dto["role"]):
                    raise Forbidden(
                        f"You do not have permission to create a user with the "
                        f"role: {dto['role']}"
                    )
                if inviter.role != UserRole.SUPER_ADMIN:
                    club_id = inviter.club_id

            if club_id:
                if not Club.objects.filter(id=club_id).exists():
                    raise Conflict(
                        "Invalid clubId: The specified Club does not exist."
                    )

            if User.objects.filter(email=dto["email"]).exists():
                raise Conflict("User with this email already exists")

            is_prod = not _is_dev()
            if is_prod:
                temp_password = (
                    "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
                    + "A1!"
                )
            else:
                temp_password = "DevPass123!"

            user = User(
                name=dto["name"],
                email=dto["email"],
                role=dto["role"],
                club_id_id=club_id,
                is_first_login=True,
            )
            user.password = hash_password(temp_password)
            user.save()

            if is_prod:
                # Raising here rolls back the user creation (transactional).
                from common.mail import send_invitation_email

                send_invitation_email(dto["email"], temp_password)
            else:
                logger.info(
                    "\n================================\n"
                    "DEVELOPMENT MODE: User Invited\n"
                    "Email: %s\nPassword: %s\n"
                    "================================\n",
                    dto["email"],
                    temp_password,
                )

            return {"message": "Invitation sent successfully", "userId": user.id}

    except (Forbidden, Conflict, NotFound):
        raise
    except Exception as exc:  # noqa: BLE001 — mirror NestJS catch-all → 500
        message = (
            f"Transaction error: {exc}"
            if _is_dev()
            else "Something went wrong. Please try again."
        )
        raise InternalServerError(message)


def find_all(query, current_user):
    page = int(query.get("page") or 1)
    limit = int(query.get("limit") or 10)
    skip = (page - 1) * limit

    qs = User.objects.all()

    # 1. Multi-tenancy isolation.
    if current_user.role != UserRole.SUPER_ADMIN:
        qs = qs.filter(club_id_id=current_user.club_id)
    elif query.get("clubId"):
        qs = qs.filter(club_id_id=query.get("clubId"))

    # 2. Hierarchy enforcement.
    subordinates = subordinate_roles(current_user.role)
    role = query.get("role")
    if role:
        if role not in subordinates and current_user.role != UserRole.SUPER_ADMIN:
            return {"data": [], "meta": {"total": 0, "page": page, "lastPage": 0}}
        qs = qs.filter(role=role)
    elif current_user.role != UserRole.SUPER_ADMIN:
        qs = qs.filter(role__in=subordinates)

    total = qs.count()
    users = list(qs[skip : skip + limit])

    return {
        "data": [list_user_dict(u) for u in users],
        "meta": {
            "total": total,
            "page": page,
            "lastPage": math.ceil(total / limit) if limit else 0,
        },
    }


def get_profile_with_context(user_id):
    user = User.objects.filter(id=user_id).first()
    if not user:
        raise NotFound("User not found")

    context = {}
    if user.role == UserRole.PLAYER:
        # roster is stored as ObjectId in the source, so this lookup matches.
        team = Team.objects.filter(roster__contains=[user_id]).first()
        if team:
            context = {
                "teamId": team.id,
                "teamName": team.name,
                "ageGroupId": team.age_group_id_id,
            }
    elif user.role == UserRole.COACH:
        # COMPATIBILITY: Preserve NestJS production behavior — context is ALWAYS
        # empty for a COACH here. The source stores Team.coachId as a plain
        # STRING but queries `Team.find({coachId: ObjectId(id)})`, so the lookup
        # never matches and `teams` is never added. Reproduced narrowly for
        # byte-parity; do NOT restore the real lookup without a coordinated
        # client change. See docs/POST_MIGRATION_CLEANUP.md (item 1).
        context = {}
    elif user.role == UserRole.COORDINATOR:
        # COMPATIBILITY: same ObjectId/string bug — AgeGroup.coordinatorId is a
        # STRING in the source, queried as ObjectId, so context is ALWAYS empty
        # for a COORDINATOR. See docs/POST_MIGRATION_CLEANUP.md (item 2).
        context = {}

    return profile_with_context_dict(user, context)


def update_profile(user_id, data):
    user = User.objects.filter(id=user_id).first()
    if not user:
        return None
    if "password" in data and data["password"]:
        user.password = hash_password(data["password"])
    if "name" in data:
        user.name = data["name"]
    if "email" in data:
        user.email = data["email"]
    if "profileImage" in data:
        user.profile_image = data["profileImage"]
    user.save()
    return updated_profile_dict(user)


def update_role(target_user_id, new_role, updater):
    # NestJS calls findById on this raw path param → malformed id CastErrors → 500.
    cast_object_id_or_500(target_user_id)
    target = User.objects.filter(id=target_user_id).first()
    # COMPATIBILITY: NestJS returns 409 (ConflictException), NOT 404, here.
    if not target:
        raise Conflict("User not found")

    if updater.role != UserRole.SUPER_ADMIN and (
        str(target.club_id_id) != str(updater.club_id)
    ):
        raise Forbidden("You cannot modify users outside of your club.")

    # Can the updater manage the target's CURRENT role? (super admin bypasses)
    if weight(updater.role) <= weight(target.role) and updater.role != UserRole.SUPER_ADMIN:
        raise Forbidden("You do not have permission to change this user's role.")

    # Can the updater assign the NEW role? (NO super-admin bypass here — matches
    # NestJS: a super admin cannot assign SUPER_ADMIN since 100 <= 100.)
    if weight(updater.role) <= weight(new_role):
        raise Forbidden(f"You do not have permission to assign the role: {new_role}")

    target.role = new_role
    target.save(update_fields=["role", "updated_at"])
    return {
        "message": "Role updated successfully",
        "user": {"id": target.id, "name": target.name, "newRole": new_role},
    }


def bootstrap_super_admin():
    """Mirror of UsersService.onModuleInit."""
    if User.objects.filter(role=UserRole.SUPER_ADMIN).exists():
        return None
    email = settings.SUPER_ADMIN_EMAIL
    password = settings.SUPER_ADMIN_PASSWORD
    user = User(name="System Admin", email=email, role=UserRole.SUPER_ADMIN,
                is_first_login=False)
    user.password = hash_password(password)
    user.save()
    logger.info(
        "\n==================================================\n"
        "INITIAL SUPER ADMIN CREATED\nEmail: %s\nPassword: %s\n"
        "==================================================\n",
        email, password,
    )
    return user
