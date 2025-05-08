from collections import defaultdict
from django.http import FileResponse
from django.utils import timezone
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.request import SAFE_METHODS

from formulas.models import (
    UserAccount,
    Follow,
    Ingredient,
    Dish,
    FavoriteRecipe,
    ShoppingCart,
)
from .pagination import PageNumberLimitPagination
from .serializers import (
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    ShortRecipeSerializer,
    SubscribedAuthorSerializer,
    PublicUserSerializer,
)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Представление для чтения ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        """Фильтрация по префиксу названия (параметр name)."""
        prefix = self.request.query_params.get("name")
        return (
            self.queryset.filter(name__istartswith=prefix.lower())
            if prefix
            else self.queryset
        )


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Dish.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = PageNumberLimitPagination

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        if author := params.get("author"):
            qs = qs.filter(creator_id=author)
        if params.get("is_in_shopping_cart") == "1" and self.request.user.is_authenticated:
            qs = qs.filter(shoppingcarts__user=self.request.user)
        if params.get("is_favorited") == "1" and self.request.user.is_authenticated:
            qs = qs.filter(favorites__user=self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @staticmethod
    def _toggle_action(request, pk, model, label):
        dish = get_object_or_404(Dish, pk=pk)

        if request.method != "POST":
            get_object_or_404(model, user=request.user, dish=dish).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        obj, created = model.objects.get_or_create(user=request.user, dish=dish)
        if not created:
            raise ValidationError({
                "error": f"Рецепт '{dish.title}' уже в {label}"
            })

        return Response(
            ShortRecipeSerializer(dish, context={"request": request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post", "delete"],
            url_path="favorite", permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        return self._toggle_action(request, pk, FavoriteRecipe, "избранном")

    @action(detail=True, methods=["post", "delete"],
            url_path="shopping_cart", permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self._toggle_action(request, pk, ShoppingCart, "корзине")

    @action(detail=False, methods=["get"],
            url_path="download_shopping_cart", permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        totals = defaultdict(int)
        dish_titles = set()

        ingredients = []

        for item in request.user.shoppingcart_set.select_related("dish"):
            dish_titles.add(item.dish.title)
            for ia in item.dish.recipe_ingredients.select_related("ingredient"):
                key = (ia.ingredient.name, ia.ingredient.measurement_unit)
                totals[key] += ia.amount

        sorted_items = sorted(totals.items(), key=lambda x: x[0][0].lower())
        today = timezone.localdate().strftime("%d.%m.%Y")
        lines = [f"Список покупок на {today}:", "Продукты:"]

        for idx, ((name, unit), amount) in enumerate(sorted_items, 1):
            lines.append(f"{idx}. {name.capitalize()} ({unit}) — {amount}")

        lines.append("\nРецепты, для которых нужны эти продукты:")
        for idx, title in enumerate(sorted(dish_titles), 1):
            lines.append(f"{idx}. {title}")

        report_text = "\n".join(lines)
        return FileResponse(
            report_text,
            content_type="text/plain",
            filename="shopping_cart.txt"
        )


class UserViewSet(DjoserUserViewSet):
    queryset = UserAccount.objects.all()
    serializer_class = PublicUserSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = PageNumberPagination

    @action(detail=False, methods=["put", "delete"], url_path="me/avatar")
    def avatar(self, request):
        if request.method != "PUT":
            request.user.profile_picture.delete(save=True)
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = self.get_serializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"avatar": serializer.data["profile_picture"]})

    @action(detail=True, methods=["post", "delete"], url_path="subscribe",
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        author = get_object_or_404(UserAccount, pk=id)

        if request.method != "POST":
            get_object_or_404(Follow, follower=request.user, following=author).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        if author == request.user:
            raise ValidationError({"error": "Нельзя подписаться на самого себя"})

        obj, created = Follow.objects.get_or_create(
            follower=request.user,
            following=author
        )
        if not created:
            raise ValidationError({
                "error": f"Вы уже подписаны на пользователя {author.username}"
            })

        serializer = PublicUserSerializer(author, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="subscriptions",
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        subscriptions = request.user.following_set.select_related("following")
        paginator = PageNumberPagination()
        paginator.page_size = int(request.GET.get("limit", 6))
        page = paginator.paginate_queryset(subscriptions, request)

        authors = [sub.following for sub in page]
        serializer = SubscribedAuthorSerializer(
            authors,
            many=True,
            context={"request": request}
        )
        return paginator.get_paginated_response(serializer.data)