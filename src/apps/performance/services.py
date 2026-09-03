"""PerformanceService — port of `src/performance/performance.service.ts`."""
from apps.users.models import User
from apps.teams.models import Team
from apps.age_groups.models import AgeGroup
from common.roles import UserRole
from common.utils import js_round
from common.tenancy import cast_object_id_or_500
from common.exceptions import NotFound, BadRequest, Forbidden
from .models import Performance
from .serializers import performance_doc_dict, default_performance_dict


def upsert_performance(player_id, dto, requester):
    cast_object_id_or_500(player_id)
    player = User.objects.filter(id=player_id).first()
    if not player:
        raise NotFound("Player not found.")
    if player.role != UserRole.PLAYER:
        raise BadRequest("Performance ratings can only be recorded for players.")
    if requester.role != UserRole.SUPER_ADMIN and str(player.club_id_id) != str(requester.club_id):
        raise Forbidden("You cannot manage players outside of your club.")

    if requester.role == UserRole.COACH:
        mine = Team.objects.filter(
            coach_id_id=requester.user_id, roster__contains=[player_id]
        ).first()
        if not mine:
            raise Forbidden("You can only rate players assigned to your team roster.")
    elif requester.role == UserRole.COORDINATOR:
        team = Team.objects.filter(roster__contains=[player_id]).first()
        if not team:
            raise Forbidden("This player is not assigned to any team.")
        ag = AgeGroup.objects.filter(id=team.age_group_id_id).first()
        if not ag or str(ag.coordinator_id_id) != str(requester.user_id):
            raise Forbidden("You can only rate players in age groups you coordinate.")

    obj, _ = Performance.objects.update_or_create(
        player_id_id=player_id,
        defaults={
            "passing": dto["passing"],
            "dribbling": dto["dribbling"],
            "shooting": dto["shooting"],
            "defense": dto["defense"],
            "stamina": dto["stamina"],
            "club_id_id": player.club_id_id,
            "recorded_by_id": requester.user_id,
        },
    )
    return performance_doc_dict(obj)


def get_performance(player_id, requester):
    cast_object_id_or_500(player_id)
    player = User.objects.filter(id=player_id).first()
    if not player:
        raise NotFound("Player not found.")
    if requester.role != UserRole.SUPER_ADMIN and str(player.club_id_id) != str(requester.club_id):
        raise Forbidden("You do not have permission to view this player.")

    if requester.role == UserRole.PLAYER:
        if str(requester.user_id) != str(player_id):
            raise Forbidden("You can only view your own performance ratings.")
    elif requester.role == UserRole.PARENT:
        parent = User.objects.filter(id=requester.user_id).first()
        children = [str(x) for x in (parent.child_player_ids if parent else [])]
        if str(player_id) not in children:
            raise Forbidden("You can only view your children's performance ratings.")

    perf = Performance.objects.filter(player_id_id=player_id).first()
    if not perf:
        return default_performance_dict(player_id)
    return performance_doc_dict(perf)


def get_team_report(team_id, requester):
    cast_object_id_or_500(team_id)
    team = Team.objects.filter(id=team_id).first()
    if not team:
        raise NotFound("Team not found.")
    if requester.role != UserRole.SUPER_ADMIN and str(team.club_id_id) != str(requester.club_id):
        raise Forbidden("You do not have permission to view this team.")

    roster = list(team.roster or [])
    performances = list(Performance.objects.filter(player_id_id__in=roster))
    count = len(performances)

    if count == 0:
        return {
            "teamId": team_id,
            "teamName": team.name,
            "average": {"passing": 0, "dribbling": 0, "shooting": 0, "defense": 0, "stamina": 0},
            "topPerformers": [],
            "individualReports": [],
        }

    names = {u.id: u.name for u in User.objects.filter(id__in=[p.player_id_id for p in performances])}
    sums = {"passing": 0, "dribbling": 0, "shooting": 0, "defense": 0, "stamina": 0}
    individual = []
    for p in performances:
        for k in sums:
            sums[k] += getattr(p, k)
        overall = js_round((p.passing + p.dribbling + p.shooting + p.defense + p.stamina) / 5)
        individual.append({
            "playerId": p.player_id_id,
            "playerName": names.get(p.player_id_id),
            "passing": p.passing,
            "dribbling": p.dribbling,
            "shooting": p.shooting,
            "defense": p.defense,
            "stamina": p.stamina,
            "overallScore": overall,
        })

    top = sorted(individual, key=lambda r: r["overallScore"], reverse=True)[:3]
    return {
        "teamId": team_id,
        "teamName": team.name,
        "average": {k: js_round(sums[k] / count) for k in sums},
        "topPerformers": top,
        "individualReports": individual,
    }
