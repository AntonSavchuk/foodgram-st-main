from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import IngredientViewSet, RecipeViewSet, UserViewSet

api_router = DefaultRouter()
api_router.register(r"accounts", UserViewSet, basename="accounts")
api_router.register(r"components", IngredientViewSet, basename="components")
api_router.register(r"dishes", RecipeViewSet, basename="dishes")

urlpatterns = [
    path("", include(api_router.urls)),
    path("auth/", include("djoser.urls.authtoken")),
    path(
        "shortcut/<int:pk>/",
        RecipeViewSet.as_view({"get": "get_short_link"}),
        name="dish-shortcut"
    ),
]
