from django.urls import path

from .views import SuperAdminStatsView

app_name = "dashboard"

urlpatterns = [
    path("dashboard/super-admin", SuperAdminStatsView.as_view()),
]
