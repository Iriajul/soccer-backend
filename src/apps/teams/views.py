"""Teams endpoints — port of `src/teams/teams.controller.ts`."""
from rest_framework.views import APIView
from rest_framework.response import Response

from common.permissions import RolesGuard
from common.roles import UserRole
from . import services
from .serializers import CreateTeamSerializer, UpdateRosterSerializer


class TeamsCollectionView(APIView):
    permission_classes = [RolesGuard]

    def get_permissions(self):
        if self.request.method == "POST":
            self.required_roles = [
                UserRole.SUPER_ADMIN, UserRole.CLUB_OWNER,
                UserRole.TECH_DIRECTOR, UserRole.COORDINATOR,
            ]
        else:  # GET has no @Roles() — any authenticated role.
            self.required_roles = None
        return super().get_permissions()

    def post(self, request):
        s = CreateTeamSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(services.create(dict(s.validated_data), request.user), status=201)

    def get(self, request):
        return Response(services.find_all(request.user.club_id))


class TeamDetailView(APIView):
    permission_classes = [RolesGuard]
    required_roles = [
        UserRole.SUPER_ADMIN, UserRole.CLUB_OWNER, UserRole.TECH_DIRECTOR
    ]  # COORDINATOR intentionally excluded from delete

    def delete(self, request, id):
        return Response(services.remove(id, request.user.club_id))


class TeamRosterView(APIView):
    permission_classes = [RolesGuard]
    required_roles = [
        UserRole.SUPER_ADMIN, UserRole.CLUB_OWNER, UserRole.TECH_DIRECTOR,
        UserRole.COORDINATOR, UserRole.COACH,
    ]

    def patch(self, request, id):
        s = UpdateRosterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(
            services.update_roster(
                id, s.validated_data["playerId"], s.validated_data["action"], request.user
            )
        )
