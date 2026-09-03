"""
Auth endpoints — port of `src/auth/auth.controller.ts`.

Five are public (authentication_classes=[] so a stale Bearer header is ignored,
matching NestJS). change-password requires a valid access token. Every route
responds with HTTP 200 (@HttpCode(200) in NestJS).
"""
from rest_framework.views import APIView
from rest_framework.response import Response

from common.permissions import JwtAuthenticated
from . import services
from .serializers import (
    LoginSerializer,
    FirstLoginResetSerializer,
    RefreshTokenSerializer,
    ForgotPasswordSerializer,
    ConfirmResetPasswordSerializer,
    ChangePasswordSerializer,
)


class _PublicView(APIView):
    authentication_classes = []  # public: never inspect the Authorization header
    permission_classes = []


class LoginView(_PublicView):
    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = services.login(s.validated_data["email"], s.validated_data["password"])
        return Response(result, status=200)


class FirstLoginResetView(_PublicView):
    def post(self, request):
        s = FirstLoginResetSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = services.reset_first_login_password(
            s.validated_data["resetToken"], s.validated_data["newPassword"]
        )
        return Response(result, status=200)


class RefreshView(_PublicView):
    def post(self, request):
        s = RefreshTokenSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = services.refresh_tokens(s.validated_data["refreshToken"])
        return Response(result, status=200)


class ForgotPasswordView(_PublicView):
    def post(self, request):
        s = ForgotPasswordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = services.forgot_password(s.validated_data["email"])
        return Response(result, status=200)


class ResetPasswordView(_PublicView):
    def post(self, request):
        s = ConfirmResetPasswordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = services.reset_password(
            s.validated_data["token"], s.validated_data["newPassword"]
        )
        return Response(result, status=200)


class ChangePasswordView(APIView):
    permission_classes = [JwtAuthenticated]

    def post(self, request):
        s = ChangePasswordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = services.change_password(
            request.user.email,
            s.validated_data["oldPassword"],
            s.validated_data["newPassword"],
        )
        return Response(result, status=200)
