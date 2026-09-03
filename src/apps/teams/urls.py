from django.urls import path

from .views import TeamsCollectionView, TeamDetailView, TeamRosterView

app_name = "teams"

urlpatterns = [
    path("teams", TeamsCollectionView.as_view()),
    path("teams/<str:id>/roster", TeamRosterView.as_view()),
    path("teams/<str:id>", TeamDetailView.as_view()),
]
