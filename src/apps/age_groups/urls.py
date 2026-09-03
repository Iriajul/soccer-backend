from django.urls import path

from .views import AgeGroupsCollectionView, AgeGroupDetailView

app_name = "age_groups"

urlpatterns = [
    path("age-groups", AgeGroupsCollectionView.as_view()),
    path("age-groups/<str:id>", AgeGroupDetailView.as_view()),
]
