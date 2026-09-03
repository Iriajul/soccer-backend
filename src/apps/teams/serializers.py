"""Teams DTOs + presenters (raw create vs populated list — kept distinct)."""
from rest_framework import serializers

from common.utils import iso_z
from common.drf_fields import mongo_id_field


class CreateTeamSerializer(serializers.Serializer):
    name = serializers.CharField()
    ageGroupId = mongo_id_field("ageGroupId")
    coachId = mongo_id_field("coachId", required=False)


class UpdateRosterSerializer(serializers.Serializer):
    playerId = mongo_id_field("playerId")
    # NestJS validates action only as a non-empty string; the "add"/"remove"
    # check is done in the service (→ 400 "Invalid action...").
    action = serializers.CharField()


def team_raw_dict(team):
    """POST /teams → raw saved doc (unpopulated ids), includes __v."""
    data = {"_id": team.id, "name": team.name, "ageGroupId": team.age_group_id_id}
    if team.coach_id_id is not None:
        data["coachId"] = team.coach_id_id
    data["clubId"] = team.club_id_id
    data["roster"] = [str(x) for x in (team.roster or [])]
    data["createdAt"] = iso_z(team.created_at)
    data["updatedAt"] = iso_z(team.updated_at)
    data["__v"] = team.version
    return data


def _populate_users(ids, fields):
    """Fetch users by id preserving order; drop missing (like Mongoose populate)."""
    from apps.users.models import User

    found = {u.id: u for u in User.objects.filter(id__in=list(ids))}
    out = []
    for _id in ids:
        u = found.get(_id)
        if not u:
            continue
        entry = {"_id": u.id}
        if "name" in fields:
            entry["name"] = u.name
        if "email" in fields:
            entry["email"] = u.email
        if "profileImage" in fields:
            entry["profileImage"] = u.profile_image or None
        out.append(entry)
    return out


def team_populated_dict(team):
    """GET /teams → ageGroupId, coachId, roster all populated; clubId raw."""
    from apps.age_groups.models import AgeGroup

    ag = AgeGroup.objects.filter(id=team.age_group_id_id).first()
    age_group = {"_id": ag.id, "name": ag.name} if ag else None

    coach = None
    if team.coach_id_id is not None:
        coach = _populate_users([team.coach_id_id], ["name", "email", "profileImage"])
        coach = coach[0] if coach else None

    return {
        "_id": team.id,
        "name": team.name,
        "clubId": team.club_id_id,
        "ageGroupId": age_group,
        "coachId": coach,
        "roster": _populate_users(list(team.roster or []), ["name", "profileImage"]),
        "createdAt": iso_z(team.created_at),
        "updatedAt": iso_z(team.updated_at),
        "__v": team.version,
    }
