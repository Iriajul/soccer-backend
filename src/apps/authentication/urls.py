from django.urls import path

from .views import (
    LoginView,
    FirstLoginResetView,
    RefreshView,
    ForgotPasswordView,
    ResetPasswordView,
    ChangePasswordView,
)

app_name = "authentication"

urlpatterns = [
    path("auth/login", LoginView.as_view()),
    path("auth/first-login-reset", FirstLoginResetView.as_view()),
    path("auth/refresh", RefreshView.as_view()),
    path("auth/forgot-password", ForgotPasswordView.as_view()),
    path("auth/reset-password", ResetPasswordView.as_view()),
    path("auth/change-password", ChangePasswordView.as_view()),
]
