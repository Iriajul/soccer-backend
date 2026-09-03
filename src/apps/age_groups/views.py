"""Age-groups endpoints — port of `src/age-groups/age-groups.controller.ts`."""
from rest_framework.views import APIView
from rest_framework.response import Response

from common.permissions import RolesGuard
from common.roles import UserRole
from . import services
from .serializers import CreateAgeGroupSerializer


class AgeGroupsCollectionView(APIView):
    permission_classes = [RolesGuard]

    def get_permissions(self):
        # POST is role-gated; GET has no @Roles() (any authenticated user).
        if self.request.method == "POST":
            self.required_roles = [
                UserRole.SUPER_ADMIN, UserRole.CLUB_OWNER, UserRole.TECH_DIRECTOR
            ]
        else:
            self.required_roles = None
        return super().get_permissions()

    def post(self, request):
        s = CreateAgeGroupSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(
            services.create(dict(s.validated_data), request.user.club_id), status=201
        )

    def get(self, request):
        return Response(services.find_all(request.user.club_id))


class AgeGroupDetailView(APIView):
    permission_classes = [RolesGuard]
    required_roles = [
        UserRole.SUPER_ADMIN, UserRole.CLUB_OWNER, UserRole.TECH_DIRECTOR
    ]

    def delete(self, request, id):
        return Response(services.remove(id, request.user.club_id))
