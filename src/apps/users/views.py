"""
Users endpoints — port of `src/users/users.controller.ts`.

All routes sit behind JwtAuthGuard + RolesGuard with NO @Roles() → any
authenticated user passes the guard; the real authorization (hierarchy /
club isolation) happens in the service layer.
"""
import os
import time
import random

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from common.permissions import RolesGuard
from . import services
from .serializers import InviteUserSerializer, UpdateProfileSerializer, UpdateRoleSerializer


class UsersInviteView(APIView):
    permission_classes = [RolesGuard]

    def post(self, request):
        serializer = InviteUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.invite_staff_member(
            dict(serializer.validated_data), inviter=request.user
        )
        return Response(result, status=201)


class UserRoleView(APIView):
    permission_classes = [RolesGuard]

    def patch(self, request, id):
        serializer = UpdateRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.update_role(
            id, serializer.validated_data["role"], request.user
        )
        return Response(result, status=200)


class UsersMeView(APIView):
    permission_classes = [RolesGuard]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        return Response(services.get_profile_with_context(request.user.user_id))

    def patch(self, request):
        serializer = UpdateProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)

        upload = request.FILES.get("profileImage")
        if upload is not None:
            data["profileImage"] = _save_profile_image(upload)

        result = services.update_profile(request.user.user_id, data)
        return Response(result)


class UsersListView(APIView):
    permission_classes = [RolesGuard]

    def get(self, request):
        result = services.find_all(request.query_params, request.user)
        return Response(result)


def _save_profile_image(upload):
    """
    Save an uploaded image to STORAGE_ROOT and return the relative path
    `/storage/<filename>`, mirroring the NestJS multer diskStorage naming:
    `${Date.now()}-${round(rand*1e9)}${ext}`.
    """
    os.makedirs(settings.STORAGE_ROOT, exist_ok=True)
    _, ext = os.path.splitext(upload.name)
    filename = f"{int(time.time() * 1000)}-{random.randint(0, 10**9)}{ext}"
    dest = os.path.join(settings.STORAGE_ROOT, filename)
    with open(dest, "wb") as fh:
        for chunk in upload.chunks():
            fh.write(chunk)
    return f"/storage/{filename}"
