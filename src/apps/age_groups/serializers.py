"""Age-groups DTO + presenters."""
from rest_framework import serializers

from common.utils import iso_z
from common.drf_fields import mongo_id_field


class CreateAgeGroupSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField(required=False)
    coordinatorId = mongo_id_field("coordinatorId", required=False)


def age_group_raw_dict(ag):
    """POST /age-groups → raw saved doc; description/coordinatorId only if set."""
    data = {"_id": ag.id, "name": ag.name}
    if ag.description is not None:
        data["description"] = ag.description
    data["clubId"] = ag.club_id_id
    if ag.coordinator_id_id is not None:
        data["coordinatorId"] = ag.coordinator_id_id
    data["createdAt"] = iso_z(ag.created_at)
    data["updatedAt"] = iso_z(ag.updated_at)
    data["__v"] = 0
    return data


def _coordinator_populated(ag):
    if ag.coordinator_id_id is None:
        return None
    from apps.users.models import User

    u = User.objects.filter(id=ag.coordinator_id_id).first()
    if not u:
        return None
    # age-groups findAll uses .lean() (no toJSON transform) → profileImage is
    # ABSENT when unset (not null), unlike the non-lean populated subdocs.
    data = {"_id": u.id, "name": u.name, "email": u.email}
    if u.profile_image:
        data["profileImage"] = u.profile_image
    return data


def _team_in_group(team):
    """Team as embedded under an age group: select(name coachId roster ageGroupId)."""
    from apps.users.models import User

    coach = None
    if team.coach_id_id is not None:
        c = User.objects.filter(id=team.coach_id_id).first()
        coach = {"_id": c.id, "name": c.name} if c else None
    return {
        "_id": team.id,
        "name": team.name,
        "coachId": coach,
        "roster": [str(x) for x in (team.roster or [])],
        "ageGroupId": team.age_group_id_id,
    }


def age_group_list_dict(ag, related_teams):
    data = {"_id": ag.id, "name": ag.name}
    if ag.description is not None:
        data["description"] = ag.description
    data["clubId"] = ag.club_id_id
    data["coordinatorId"] = _coordinator_populated(ag)
    data["createdAt"] = iso_z(ag.created_at)
    data["updatedAt"] = iso_z(ag.updated_at)
    data["__v"] = 0
    data["totalTeams"] = len(related_teams)
    data["teams"] = [_team_in_group(t) for t in related_teams]
    return data
