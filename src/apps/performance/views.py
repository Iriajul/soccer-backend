"""Performance endpoints — port of `src/performance/performance.controller.ts`."""
from rest_framework.views import APIView
from rest_framework.response import Response

from common.permissions import RolesGuard
from common.roles import UserRole
from . import services
from .serializers import UpdatePerformanceSerializer

_STAFF = [
    UserRole.SUPER_ADMIN, UserRole.CLUB_OWNER, UserRole.TECH_DIRECTOR,
    UserRole.COORDINATOR, UserRole.COACH,
]


class PerformancePlayerView(APIView):
    permission_classes = [RolesGuard]

    def get_permissions(self):
        # PUT is staff-only; GET has no @Roles() (service enforces visibility).
        self.required_roles = _STAFF if self.request.method == "PUT" else None
        return super().get_permissions()

    def put(self, request, playerId):
        s = UpdatePerformanceSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(
            services.upsert_performance(playerId, dict(s.validated_data), request.user)
        )

    def get(self, request, playerId):
        return Response(services.get_performance(playerId, request.user))


class PerformanceTeamReportView(APIView):
    permission_classes = [RolesGuard]
    required_roles = _STAFF

    def get(self, request, teamId):
        return Response(services.get_team_report(teamId, request.user))
