"""ClubsService — port of `src/clubs/clubs.service.ts`."""
from django.db import transaction

from apps.users import services as users_service
from common.roles import UserRole
from common.tenancy import is_super, cast_object_id_or_500
from common.exceptions import (
    BadRequest, NotFound, Forbidden, InternalServerError,
)
from .models import Club
from .serializers import (
    club_raw_dict, my_club_dict, club_list_item, club_detail_dict,
)


def create_club(dto):
    """
    Create the Club AND its CLUB_OWNER in one transaction. ANY failure
    (including a duplicate owner email) is rolled back and surfaced as the
    exact NestJS 500 message — NOT the underlying 409.
    """
    try:
        with transaction.atomic():
            club = Club.objects.create(name=dto["name"], is_active=True)
            users_service.invite_staff_member(
                {
                    "name": dto["ownerName"],
                    "email": dto["ownerEmail"],
                    "role": UserRole.CLUB_OWNER,
                    "clubId": club.id,
                },
                inviter=None,  # club creation skips hierarchy/tenancy checks
            )
            return {
                "message": "Club and Club Owner created successfully",
                "club": club_raw_dict(club),
            }
    except Exception:
        raise InternalServerError(
            "Failed to create club and owner. Transaction rolled back."
        )


def find_all():
    return [club_list_item(c) for c in Club.objects.all()]


def get_my_club(club_id):
    if not club_id:
        raise BadRequest("Your account is not assigned to any club.")
    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFound("Club not found.")
    return my_club_dict(club)


def find_one(club_id, requester):
    # Multi-tenant check runs BEFORE the DB lookup, exactly as NestJS: a
    # non-super-admin whose clubId != :id gets 403 (even for a malformed :id).
    if not is_super(requester) and str(requester.club_id) != str(club_id):
        raise Forbidden("You do not have permission to view this club.")

    # Reached only by super admin (or a matching own club) — a malformed id
    # here hits Mongoose findById → CastError → 500.
    cast_object_id_or_500(club_id)

    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFound("Club not found.")
    return club_detail_dict(club)
