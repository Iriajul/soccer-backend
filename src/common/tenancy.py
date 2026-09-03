"""
Small helpers for the repeated authorization checks documented in
PROJECT_DOCUMENTATION.md §4.3. These stay minimal (booleans + an ObjectId
guard) because each endpoint raises its OWN specific message and status code
(sometimes 403, sometimes 404) — so the message is chosen in the service, not
here.
"""
from .roles import UserRole
from .objectid import is_object_id
from .exceptions import CastError500


def is_super(principal) -> bool:
    return principal.role == UserRole.SUPER_ADMIN


def same_club(a, b) -> bool:
    """String-compare two club ids (handles ObjectId/str, None-safe)."""
    if a is None or b is None:
        return False
    return str(a) == str(b)


def cast_object_id_or_500(value):
    """
    Reproduce the Mongoose CastError → 500 quirk on the UNGUARDED routes
    (DELETE /teams/:id, PATCH /teams/:id/roster, GET /events/team/:teamId):
    a malformed ObjectId path param must 500 with the timestamp/path body,
    NOT a clean 400/404.

    # COMPATIBILITY: Preserve NestJS production behavior.
    # Do not "fix" this into a 400/404 without a coordinated client change.
    """
    if not is_object_id(value):
        raise CastError500(value)
    return value
