from collections import defaultdict

from django.http import FileResponse
from django.utils import timezone

from djoser.views import UserViewSet as BaseUserViewSet
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.exceptions import ValidationError

from formulas.models import Ingredient, Dish, FavoriteRecipe, ShoppingCartRecipe
from users.models import CustomUser, Follow

from .pagination import CustomPagination
from .serializers import (
    IngredientDataSerializer,
    FullRecipeSerializer,
    MiniDishSerializer,
    AuthorWithDishesSerializer,
    ExtendedUserSerializer,
)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Предоставляет список ингредиентов, доступный только для чтения."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientDataSerializer
    pagination_class = None

    def get_queryset(self):
        query = self.request.query_params.get("name")
        return (
            self.queryset.filter(name__istartswith=query.lower())
            if query
            else self.queryset
        )


class RecipeViewSet(viewsets.ModelViewSet):
    """Полный набор операций с рецептами."""
    queryset = Dish.objects.all()
    serializer_class = FullRecipeSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = CustomPagination

    def get_queryset(self):
        dishes = super().get_queryset()
        user = self.request.user
        params = self.request.query_params

        if author_id := params.get("author"):
            dishes = dishes.filter(creator_id=author_id)

        if params.get("is_favorited") == "1" and user.is_authenticated:
            dishes = dishes.filter(favorites__user=user)

        if params.get("is_in_shopping_cart") == "1" and user.is_authenticated:
            dishes = dishes.filter(shoppingcarts__user=user)

        return dishes

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @staticmethod
    def _handle_toggle(request, dish, model_cls):
        if request.method == "POST":
            obj, created = model_cls.objects.get_or_create(user=request.user, dish=dish)
            if not created:
                raise ValidationError({"error": "Уже существует."})
            return Response(MiniDishSerializer(dish).data, status=status.HTTP_201_CREATED)
        model_cls.objects.filter(user=request.user, dish=dish).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post", "delete"], url_path="favorite")
    def mark_favorite(self, request, pk=None):
        dish = get_object_or_404(Dish, pk=pk)
        return self._handle_toggle(request, dish, FavoriteRecipe)

    @action(detail=True, methods=["post", "delete"], url_path="shopping_cart")
    def add_to_cart(self, request, pk=None):
        dish = get_object_or_404(Dish, pk=pk)
        return self._handle_toggle(request, dish, ShoppingCartRecipe)

    @action(detail=True, methods=["get"], url_path="get-link")
    def generate_short_link(self, request, pk=None):
        short_url = request.build_absolute_uri(reverse("dish-shortcut", args=[pk]))
        return Response({"short-link": short_url})

    @action(detail=False, methods=["get"], url_path="download_shopping_cart")
    def download_cart(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Необходима авторизация."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        total_ingredients = defaultdict(int)
        used_dishes = set()

        for entry in request.user.shopping_cart_recipes.select_related("dish"):
            used_dishes.add(entry.dish.title)
            for item in entry.dish.recipe_ingredients.select_related("ingredient"):
                key = (item.ingredient.name, item.ingredient.measurement_unit)
                total_ingredients[key] += item.amount

        today = timezone.localdate().strftime("%d.%m.%Y")
        lines = [f"Список покупок на {today}:", "Состав:"]

        for idx, ((name, unit), quantity) in enumerate(sorted(total_ingredients.items()), 1):
            lines.append(f"{idx}. {name.capitalize()} ({unit}) — {quantity}")

        lines.append("\nРецепты:")
        for idx, title in enumerate(sorted(used_dishes), 1):
            lines.append(f"{idx}. {title}")

        content = "\n".join(lines)
        return FileResponse(content, content_type="text/plain", filename="shopping_cart.txt")


class UserViewSet(BaseUserViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = ExtendedUserSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = CustomPagination

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated], url_path="me")
    def current_user(self, request):
        return Response(self.get_serializer(request.user).data)

    @action(detail=False, methods=["put", "delete"], url_path="me/avatar")
    def manage_avatar(self, request):
        user = request.user
        if request.method == "PUT":
            serializer = self.get_serializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"avatar": serializer.data.get("profile_picture")})
        user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post", "delete"], url_path="subscribe")
    def manage_subscription(self, request, id=None):
        author = get_object_or_404(CustomUser, pk=id)
        if author == request.user:
            raise ValidationError({"error": "Нельзя подписываться на себя."})

        if request.method == "POST":
            obj, created = Follow.objects.get_or_create(subscriber=request.user, author=author)
            if not created:
                raise ValidationError({"error": "Вы уже подписаны."})
            return Response(
                {"user": obj.subscriber.username, "author": author.username},
                status=status.HTTP_201_CREATED
            )

        Follow.objects.filter(subscriber=request.user, author=author).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="subscriptions")
    def list_subscriptions(self, request):
        follows = (
            request.user.subscriptions.select_related("author")
            if request.user.is_authenticated
            else Follow.objects.none()
        )

        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get("limit", 6))
        page = paginator.paginate_queryset(follows, request)

        authors = [f.author for f in page]
        serializer = AuthorWithDishesSerializer(authors, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)
