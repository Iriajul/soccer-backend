"""Dashboard endpoint — port of `src/dashboard/dashboard.controller.ts`."""
from rest_framework.views import APIView
from rest_framework.response import Response

from common.permissions import RolesGuard
from common.roles import UserRole
from . import services


class SuperAdminStatsView(APIView):
    permission_classes = [RolesGuard]
    required_roles = [UserRole.SUPER_ADMIN]

    def get(self, request):
        return Response(services.get_super_admin_stats())
