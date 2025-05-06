from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from django.shortcuts import get_object_or_404
from formulas.models import Dish, FavoriteRecipe, ShoppingCartRecipe
from formulas.serializers import DishSerializer, ShortDishSerializer
from api.pagination import CustomPagination


class DishViewSet(viewsets.ModelViewSet):
    queryset = Dish.objects.all()
    serializer_class = DishSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = CustomPagination

    def get_queryset(self):
        qs = super().get_queryset()
        author = self.request.query_params.get("author")
        if author:
            qs = qs.filter(creator__id=author)
        return qs

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @staticmethod
    def _toggle_recipe_in_list(request, recipe, model):
        if request.method == "POST":
            obj, created = model.objects.get_or_create(
                user=request.user,
                dish=recipe,
            )
            if not created:
                raise ValidationError({"error": "Рецепт уже добавлен"})
            return Response(
                ShortDishSerializer(recipe).data,
                status=status.HTTP_201_CREATED,
            )

        get_object_or_404(model, user=request.user, dish=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post", "delete"], url_path="favorite")
    def favorite(self, request, pk=None):
        dish = get_object_or_404(Dish, pk=pk)
        return self._toggle_recipe_in_list(request, dish, FavoriteRecipe)

    @action(detail=True, methods=["post", "delete"], url_path="shopping_cart")
    def shopping_cart(self, request, pk=None):
        dish = get_object_or_404(Dish, pk=pk)
        return self._toggle_recipe_in_list(request, dish, ShoppingCartRecipe)
