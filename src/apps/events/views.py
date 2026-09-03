"""Events endpoints — port of `src/events/events.controller.ts`."""
from rest_framework.views import APIView
from rest_framework.response import Response

from common.permissions import RolesGuard
from common.roles import UserRole
from . import services
from .serializers import CreateEventSerializer


class EventsCreateView(APIView):
    permission_classes = [RolesGuard]
    required_roles = [
        UserRole.SUPER_ADMIN, UserRole.CLUB_OWNER, UserRole.TECH_DIRECTOR,
        UserRole.COORDINATOR, UserRole.COACH,
    ]

    def post(self, request):
        s = CreateEventSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(services.create(dict(s.validated_data), request.user), status=201)


class EventScheduleView(APIView):
    permission_classes = [RolesGuard]  # no @Roles() — any authenticated role

    def get(self, request, teamId):
        return Response(services.get_schedules_by_team(teamId, request.user))
