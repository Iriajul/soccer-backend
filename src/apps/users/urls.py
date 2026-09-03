from django.urls import path

from .views import UsersInviteView, UserRoleView, UsersMeView, UsersListView

app_name = "users"

urlpatterns = [
    path("users/invite", UsersInviteView.as_view()),
    path("users/me", UsersMeView.as_view()),
    path("users/<str:id>/role", UserRoleView.as_view()),
    path("users", UsersListView.as_view()),
]
