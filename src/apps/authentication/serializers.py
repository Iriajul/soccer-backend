"""
Auth request DTOs — mirror the class-validator DTOs in auth.controller.ts.

Error messages approximate class-validator wording ("email must be an email",
"<field> should not be empty"). Exact validation-array parity is a
golden-master follow-up.
"""
from rest_framework import serializers


def _required_str(field):
    return serializers.CharField(
        error_messages={
            "blank": f"{field} should not be empty",
            "required": f"{field} should not be empty",
            "null": f"{field} should not be empty",
        }
    )


def _email():
    return serializers.EmailField(
        error_messages={
            "invalid": "email must be an email",
            "blank": "email should not be empty",
            "required": "email should not be empty",
        }
    )


class LoginSerializer(serializers.Serializer):
    email = _email()
    password = _required_str("password")


class FirstLoginResetSerializer(serializers.Serializer):
    resetToken = _required_str("resetToken")
    newPassword = _required_str("newPassword")


class RefreshTokenSerializer(serializers.Serializer):
    refreshToken = _required_str("refreshToken")


class ForgotPasswordSerializer(serializers.Serializer):
    email = _email()


class ConfirmResetPasswordSerializer(serializers.Serializer):
    token = _required_str("token")
    newPassword = _required_str("newPassword")


class ChangePasswordSerializer(serializers.Serializer):
    oldPassword = _required_str("oldPassword")
    newPassword = _required_str("newPassword")
