"""Маршруты API-приложения: ViewSet'ы и вспомогательные endpoints."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import IngredientViewSet, RecipeViewSet, UserViewSet

api_router = DefaultRouter()
api_router.register(r"users", UserViewSet, basename="users")
api_router.register(r"ingredients", IngredientViewSet, basename="ingredients")
api_router.register(r"recipes", RecipeViewSet, basename="recipes")

urlpatterns = [
    path("", include(api_router.urls)),
    path("auth/", include("djoser.urls.authtoken")),
    path(
        "shortcut/<int:pk>/",
        RecipeViewSet.as_view({"get": "get_short_link"}),
        name="dish-shortcut"
    ),
]
