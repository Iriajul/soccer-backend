from django.urls import path

from .views import (
    ConnectionRequestView, ConnectionPendingView, ConnectionApproveView,
    ConnectionRejectView, MyChildrenView, MyParentsView,
)

app_name = "connections"

urlpatterns = [
    path("connections/request", ConnectionRequestView.as_view()),
    path("connections/pending", ConnectionPendingView.as_view()),
    path("connections/my-children", MyChildrenView.as_view()),
    path("connections/my-parents", MyParentsView.as_view()),
    path("connections/<str:id>/approve", ConnectionApproveView.as_view()),
    path("connections/<str:id>/reject", ConnectionRejectView.as_view()),
]
