"""Clubs endpoints — port of `src/clubs/clubs.controller.ts`."""
from rest_framework.views import APIView
from rest_framework.response import Response

from common.permissions import RolesGuard
from common.roles import UserRole
from . import services
from .serializers import CreateClubSerializer


class ClubsCollectionView(APIView):
    """POST /clubs and GET /clubs — both SUPER_ADMIN only."""

    permission_classes = [RolesGuard]
    required_roles = [UserRole.SUPER_ADMIN]

    def post(self, request):
        s = CreateClubSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(services.create_club(dict(s.validated_data)), status=201)

    def get(self, request):
        return Response(services.find_all())


class MyClubView(APIView):
    permission_classes = [RolesGuard]  # any authenticated user

    def get(self, request):
        return Response(services.get_my_club(request.user.club_id))


class ClubDetailView(APIView):
    permission_classes = [RolesGuard]  # any authenticated user

    def get(self, request, id):
        return Response(services.find_one(id, request.user))
