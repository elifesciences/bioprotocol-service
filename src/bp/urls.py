from django.urls import path
from . import views

urlpatterns = [
    path("ping", views.ping, name="ping"),
    path("status", views.status, name="status"),
    path("bioprotocol/article/<int:msid>", views.article, name="article"),
]
