"""EventsService — port of `src/events/events.service.ts`."""
from apps.teams.models import Team
from common.roles import UserRole
from common.tenancy import cast_object_id_or_500
from common.exceptions import NotFound, Forbidden
from .models import Event
from .serializers import event_raw_dict, event_schedule_dict


def create(dto, requester):
    team = Team.objects.filter(id=dto["teamId"]).first()
    if not team:
        raise NotFound("Team not found")

    if requester.role != UserRole.SUPER_ADMIN and str(team.club_id_id) != str(requester.club_id):
        raise Forbidden("Cannot create events for teams outside your club.")

    if requester.role == UserRole.COACH and str(team.coach_id_id) != str(requester.user_id):
        raise Forbidden("You can only create events for your own team.")

    ev = Event(
        title=dto["title"],
        description=dto["description"],
        date=dto["date"],
        team_id_id=dto["teamId"],
        club_id_id=team.club_id_id,      # set server-side from the team
        created_by_id=requester.user_id,  # set server-side from the JWT
    )
    ev.save()
    return event_raw_dict(ev)


def get_schedules_by_team(team_id, requester):
    cast_object_id_or_500(team_id)  # malformed id → 500 (documented quirk)
    team = Team.objects.filter(id=team_id).first()
    if not team:
        raise NotFound("Team not found")

    if requester.role != UserRole.SUPER_ADMIN and str(team.club_id_id) != str(requester.club_id):
        raise Forbidden("You cannot view schedules for this team.")

    events = Event.objects.filter(team_id_id=team_id).order_by("date")  # ascending
    return [event_schedule_dict(e) for e in events]
