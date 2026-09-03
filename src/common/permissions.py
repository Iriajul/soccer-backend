"""
DRF permissions mirroring NestJS guards.

- `JwtAuthenticated` = JwtAuthGuard (token required).
- `RolesGuard` = the NestJS RolesGuard: a view with no `required_roles`
  admits ANY authenticated user; otherwise the role must be in the list,
  else a 403 "Requires one of these roles: ..." (exact NestJS wording).

Ownership/club-isolation rules are enforced in the service layer (see
`common.tenancy`), exactly as NestJS does inside its services.
"""
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import NotAuthenticated

from .exceptions import Forbidden


def _require_auth(request):
    principal = getattr(request, "user", None)
    if not principal or not getattr(principal, "is_authenticated", False):
        raise NotAuthenticated("Unauthorized")
    return principal


class JwtAuthenticated(BasePermission):
    def has_permission(self, request, view):
        _require_auth(request)
        return True


class RolesGuard(BasePermission):
    """
    Reads `view.required_roles` (a list of role strings). Empty/absent means
    "any authenticated user" — matching RolesGuard returning true when a route
    carries no @Roles() metadata.
    """

    def has_permission(self, request, view):
        principal = _require_auth(request)
        roles = getattr(view, "required_roles", None)
        if not roles:
            return True
        if principal.role not in roles:
            raise Forbidden(f"Requires one of these roles: {', '.join(roles)}")
        return True
