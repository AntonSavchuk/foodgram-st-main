from django.urls import path
from .views import short_link_view

urlpatterns = [
    path("short-link/<int:pk>/", short_link_view, name="dish-short-link"),
]
