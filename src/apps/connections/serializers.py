"""Connections DTO + presenters."""
from rest_framework import serializers

from common.utils import iso_z
from common.drf_fields import mongo_id_field


class CreateConnectionSerializer(serializers.Serializer):
    parentId = mongo_id_field("parentId")
    childId = mongo_id_field("childId")


def connection_raw_dict(req):
    """createRequest / approve / reject → raw doc (parent/child NOT populated)."""
    return {
        "_id": req.id,
        "requesterId": req.requester_id_id,
        "parentId": req.parent_id_id,
        "childId": req.child_id_id,
        "clubId": req.club_id_id,
        "status": req.status,
        "createdAt": iso_z(req.created_at),
        "updatedAt": iso_z(req.updated_at),
        "__v": 0,
    }


def connection_populated_dict(req):
    """GET /connections/pending → parentId/childId populated to {_id,name,email}."""
    from apps.users.models import User

    ids = [req.parent_id_id, req.child_id_id]
    users = {u.id: u for u in User.objects.filter(id__in=ids)}

    def pop(uid):
        u = users.get(uid)
        if not u:
            return None
        # populate(..., 'name email') is non-lean → toJSON transform adds
        # profileImage (null when unset).
        return {"_id": u.id, "name": u.name, "email": u.email,
                "profileImage": u.profile_image or None}

    return {
        "_id": req.id,
        "requesterId": req.requester_id_id,
        "parentId": pop(req.parent_id_id),
        "childId": pop(req.child_id_id),
        "clubId": req.club_id_id,
        "status": req.status,
        "createdAt": iso_z(req.created_at),
        "updatedAt": iso_z(req.updated_at),
        "__v": 0,
    }
