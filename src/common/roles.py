"""
Role definitions and hierarchy — a direct port of
`src/users/schemas/user.schema.ts` (UserRole + RoleWeights).

COMPATIBILITY: role STRINGS must never change; management/invite authority is
based on STRICTLY GREATER weight (`>`, never `>=`).
"""
from django.db import models


class UserRole(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", "SUPER_ADMIN"
    CLUB_OWNER = "CLUB_OWNER", "CLUB_OWNER"
    TECH_DIRECTOR = "TECH_DIRECTOR", "TECH_DIRECTOR"
    COORDINATOR = "COORDINATOR", "COORDINATOR"
    COACH = "COACH", "COACH"
    PLAYER = "PLAYER", "PLAYER"
    PARENT = "PARENT", "PARENT"


# Exact weights from RoleWeights in the NestJS schema.
ROLE_WEIGHTS = {
    UserRole.SUPER_ADMIN: 100,
    UserRole.CLUB_OWNER: 90,
    UserRole.TECH_DIRECTOR: 80,
    UserRole.COORDINATOR: 70,
    UserRole.COACH: 60,
    UserRole.PLAYER: 50,
    UserRole.PARENT: 50,
}


def weight(role: str) -> int:
    return ROLE_WEIGHTS[UserRole(role)]


def outranks(actor_role: str, target_role: str) -> bool:
    """True iff actor can act on/assign target_role (STRICTLY greater weight)."""
    return weight(actor_role) > weight(target_role)


def subordinate_roles(actor_role: str):
    """Roles with strictly lower weight than the actor (used by GET /users)."""
    my = weight(actor_role)
    return [r.value for r in UserRole if ROLE_WEIGHTS[r] < my]
