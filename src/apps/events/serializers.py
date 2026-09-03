"""Events DTO + presenters (raw create vs populated schedule)."""
from rest_framework import serializers

from common.utils import iso_z
from common.drf_fields import mongo_id_field


class CreateEventSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField()
    date = serializers.DateTimeField(
        error_messages={"invalid": "date must be a valid ISO 8601 date string"}
    )
    teamId = mongo_id_field("teamId")


def event_raw_dict(ev):
    """POST /events → raw doc; teamId/clubId/createdBy are plain id strings."""
    return {
        "_id": ev.id,
        "title": ev.title,
        "description": ev.description,
        "date": iso_z(ev.date),
        "teamId": ev.team_id_id,
        "clubId": ev.club_id_id,
        "createdBy": ev.created_by_id,
        "createdAt": iso_z(ev.created_at),
        "updatedAt": iso_z(ev.updated_at),
        "__v": 0,
    }


def event_schedule_dict(ev):
    """GET /events/team/:teamId → createdBy populated to {_id, name} only."""
    from apps.users.models import User

    creator = User.objects.filter(id=ev.created_by_id).first()
    # populate('createdBy','name') is non-lean → the User toJSON transform adds
    # profileImage (null when unset) even though only `name` was selected.
    created_by = (
        {"_id": creator.id, "name": creator.name, "profileImage": creator.profile_image or None}
        if creator else None
    )
    return {
        "_id": ev.id,
        "title": ev.title,
        "description": ev.description,
        "date": iso_z(ev.date),
        "teamId": ev.team_id_id,
        "clubId": ev.club_id_id,
        "createdBy": created_by,
        "createdAt": iso_z(ev.created_at),
        "updatedAt": iso_z(ev.updated_at),
        "__v": 0,
    }
