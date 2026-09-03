from django.urls import path

from .views import ClubsCollectionView, MyClubView, ClubDetailView

app_name = "clubs"

urlpatterns = [
    path("clubs", ClubsCollectionView.as_view()),
    path("clubs/my-club", MyClubView.as_view()),   # before <id> so it isn't captured
    path("clubs/<str:id>", ClubDetailView.as_view()),
]
