"""Performance DTO + presenters."""
from rest_framework import serializers

from common.utils import iso_z


def _rating_field(name):
    return serializers.IntegerField(
        min_value=0,
        max_value=100,
        error_messages={
            "max_value": f"{name} must not be greater than 100",
            "min_value": f"{name} must not be less than 0",
            "required": f"{name} should not be empty",
            "invalid": f"{name} must be a number conforming to the specified constraints",
        },
    )


class UpdatePerformanceSerializer(serializers.Serializer):
    passing = _rating_field("passing")
    dribbling = _rating_field("dribbling")
    shooting = _rating_field("shooting")
    defense = _rating_field("defense")
    stamina = _rating_field("stamina")


def performance_doc_dict(p):
    return {
        "_id": p.id,
        "playerId": p.player_id_id,
        "clubId": p.club_id_id,
        "passing": p.passing,
        "dribbling": p.dribbling,
        "shooting": p.shooting,
        "defense": p.defense,
        "stamina": p.stamina,
        "recordedBy": p.recorded_by_id,
        "createdAt": iso_z(p.created_at),
        "updatedAt": iso_z(p.updated_at),
        "__v": 0,
    }


def default_performance_dict(player_id):
    """GET /performance/:playerId when no record exists (200, not 404)."""
    return {
        "playerId": player_id,
        "passing": 0,
        "dribbling": 0,
        "shooting": 0,
        "defense": 0,
        "stamina": 0,
        "recordedBy": None,
    }
