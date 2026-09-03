from django.urls import path

from .views import PerformancePlayerView, PerformanceTeamReportView

app_name = "performance"

urlpatterns = [
    path("performance/team/<str:teamId>/report", PerformanceTeamReportView.as_view()),
    path("performance/<str:playerId>", PerformancePlayerView.as_view()),
]
