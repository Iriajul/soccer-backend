"""AgeGroupsService — port of `src/age-groups/age-groups.service.ts`."""
from apps.teams.models import Team
from common.tenancy import cast_object_id_or_500
from common.exceptions import Conflict, NotFound
from .models import AgeGroup
from .serializers import age_group_raw_dict, age_group_list_dict


def create(dto, club_id):
    # Duplicate-name check within the club. A super admin (club_id None) checks
    # the name globally, mirroring Mongoose dropping the undefined clubId.
    dup = AgeGroup.objects.filter(name=dto["name"])
    if club_id is not None:
        dup = dup.filter(club_id_id=club_id)
    if dup.exists():
        raise Conflict(f"An Age Group named '{dto['name']}' already exists in your club.")

    ag = AgeGroup(name=dto["name"], club_id_id=club_id)
    if "description" in dto:
        ag.description = dto["description"]
    if "coordinatorId" in dto:
        ag.coordinator_id_id = dto["coordinatorId"]
    ag.save()
    return age_group_raw_dict(ag)


def find_all(club_id):
    ags = AgeGroup.objects.all()
    teams = Team.objects.all()
    if club_id is not None:
        ags = ags.filter(club_id_id=club_id)
        teams = teams.filter(club_id_id=club_id)

    teams = list(teams)
    result = []
    for ag in ags:
        related = [t for t in teams if str(t.age_group_id_id) == str(ag.id)]
        result.append(age_group_list_dict(ag, related))
    return result


def remove(age_group_id, club_id):
    cast_object_id_or_500(age_group_id)
    qs = AgeGroup.objects.filter(id=age_group_id)
    if club_id is not None:
        qs = qs.filter(club_id_id=club_id)
    obj = qs.first()
    if not obj:
        raise NotFound(
            "Age group not found or you do not have permission to delete it."
        )
    obj.delete()
    return {"message": "Age group deleted successfully"}
