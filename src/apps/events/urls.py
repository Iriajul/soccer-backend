from django.urls import path

from .views import EventsCreateView, EventScheduleView

app_name = "events"

urlpatterns = [
    path("events", EventsCreateView.as_view()),
    path("events/team/<str:teamId>", EventScheduleView.as_view()),
]
