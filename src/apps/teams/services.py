"""TeamsService — port of `src/teams/teams.service.ts`."""
from apps.age_groups.models import AgeGroup
from common.roles import UserRole
from common.tenancy import cast_object_id_or_500
from common.exceptions import NotFound, Forbidden, Conflict, BadRequest
from .models import Team
from .serializers import team_raw_dict, team_populated_dict


def create(dto, creator):
    ag = AgeGroup.objects.filter(id=dto["ageGroupId"]).first()
    # NOTE: no super-admin bypass — a super admin (club_id None) always fails
    # this equality and gets 404, exactly like NestJS.
    if not ag or str(ag.club_id_id) != str(creator.club_id):
        raise NotFound("Age Group not found in your club.")

    if creator.role == UserRole.COORDINATOR:
        if str(ag.coordinator_id_id) != str(creator.user_id):
            raise Forbidden(
                "You can only create teams within Age Groups you are assigned "
                "to coordinate."
            )

    team = Team(
        name=dto["name"],
        age_group_id_id=dto["ageGroupId"],
        coach_id_id=dto.get("coachId"),  # not validated for existence
        club_id_id=creator.club_id,
        roster=[],
    )
    team.save()
    return team_raw_dict(team)


def find_all(club_id):
    qs = Team.objects.all()
    if club_id is not None:  # super admin (None) sees all clubs' teams
        qs = qs.filter(club_id_id=club_id)
    return [team_populated_dict(t) for t in qs]


def remove(team_id, club_id):
    cast_object_id_or_500(team_id)
    qs = Team.objects.filter(id=team_id)
    if club_id is not None:
        qs = qs.filter(club_id_id=club_id)
    team = qs.first()
    if not team:
        raise NotFound("Team not found or you do not have permission to delete it.")
    team.delete()
    return {"message": "Team deleted successfully"}


def update_roster(team_id, player_id, action, requester):
    cast_object_id_or_500(team_id)
    qs = Team.objects.filter(id=team_id)
    if requester.club_id is not None:
        qs = qs.filter(club_id_id=requester.club_id)
    team = qs.first()
    if not team:
        raise NotFound("Team not found in your club.")

    if requester.role == UserRole.COACH and str(team.coach_id_id) != str(requester.user_id):
        raise Forbidden(
            "You can only modify the roster of the team you are assigned to coach."
        )
    if requester.role == UserRole.COORDINATOR:
        ag = AgeGroup.objects.filter(id=team.age_group_id_id).first()
        coordinator = ag.coordinator_id_id if ag else None
        if str(coordinator) != str(requester.user_id):
            raise Forbidden("You can only modify teams within your assigned Age Group.")

    roster = list(team.roster or [])
    if action == "add":
        if player_id in roster:
            raise Conflict("Player is already on this roster.")
        roster.append(player_id)
    elif action == "remove":
        roster = [x for x in roster if str(x) != str(player_id)]
    else:
        raise BadRequest('Invalid action. Use "add" or "remove".')

    team.roster = roster
    # Mongoose bumps __v on each roster-mutation save().
    team.version = (team.version or 0) + 1
    team.save(update_fields=["roster", "version", "updated_at"])
    # COMPATIBILITY: NestJS builds `Player ${action}ed successfully`, which
    # yields the misspelled "Player removeed successfully" for remove. KEEP IT.
    return {
        "message": f"Player {action}ed successfully",
        "roster": [str(x) for x in roster],
    }
