"""Clubs request DTO + response presenters (exact shapes per endpoint)."""
from rest_framework import serializers

from common.utils import iso_z
from common.roles import UserRole


class CreateClubSerializer(serializers.Serializer):
    name = serializers.CharField()
    ownerName = serializers.CharField()
    ownerEmail = serializers.EmailField()


def club_raw_dict(club):
    """POST /clubs → the raw saved Mongoose doc (includes __v)."""
    return {
        "_id": club.id,
        "name": club.name,
        "isActive": club.is_active,
        "createdAt": iso_z(club.created_at),
        "updatedAt": iso_z(club.updated_at),
        "__v": 0,
    }


def my_club_dict(club):
    """GET /clubs/my-club → club doc via .select('-__v') (NO __v)."""
    return {
        "_id": club.id,
        "name": club.name,
        "isActive": club.is_active,
        "createdAt": iso_z(club.created_at),
        "updatedAt": iso_z(club.updated_at),
    }


def _owner_dict(owner, include_created):
    if owner is None:
        return None
    data = {
        "id": owner.id,
        "name": owner.name,
        "email": owner.email,
        "profileImage": owner.profile_image or None,
    }
    if include_created:
        data["createdAt"] = iso_z(owner.created_at)
    data["isDefaultPassword"] = owner.is_first_login
    return data


def _lookup_owner_and_count(club):
    from apps.users.models import User

    owner = User.objects.filter(
        club_id_id=club.id, role=UserRole.CLUB_OWNER
    ).first()
    total = User.objects.filter(club_id_id=club.id).count()
    return owner, total


def club_list_item(club):
    """GET /clubs item: owner WITHOUT createdAt."""
    owner, total = _lookup_owner_and_count(club)
    return {
        "_id": club.id,
        "name": club.name,
        "isActive": club.is_active,
        "createdAt": iso_z(club.created_at),
        "updatedAt": iso_z(club.updated_at),
        "owner": _owner_dict(owner, include_created=False),
        "totalMembers": total,
    }


def club_detail_dict(club):
    """GET /clubs/:id: owner WITH createdAt (differs from the list item)."""
    owner, total = _lookup_owner_and_count(club)
    return {
        "_id": club.id,
        "name": club.name,
        "isActive": club.is_active,
        "createdAt": iso_z(club.created_at),
        "updatedAt": iso_z(club.updated_at),
        "owner": _owner_dict(owner, include_created=True),
        "totalMembers": total,
    }
