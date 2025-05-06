"""ViewSet'ы для работы с рецептами, пользователями и ингредиентами."""

from collections import defaultdict

from django.http import FileResponse
from django.utils import timezone

from djoser.views import UserViewSet as DjoserUserViewSet

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly
                                        )
from rest_framework.response import Response
from rest_framework.reverse import reverse

from formulas.models import (
    Ingredient,
    Dish,
    FavoriteRecipe,
    ShoppingCartRecipe,
)

from users.models import CustomUser, Follow

from .pagination import CustomPagination
from .serializers import (
    IngredientSerializer,
    RecipeSerializer,
    ShortRecipeSerializer,
    SubscribedAuthorSerializer,
    PublicUserSerializer,
)  # сериализаторы API


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
    """CRUD-действия для рецептов и доп. функции (избранное, корзина, экспорт)."""

    queryset = Dish.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = CustomPagination

    @staticmethod
    def _toggle(request, dish, model):
        """Обработка POST/DELETE для избранного или корзины."""
        if request.method == "POST":
            obj, created = model.objects.get_or_create(user=request.user, dish=dish)
            if not created:
                raise ValidationError({"error": "Уже добавлено"})
            return Response(ShortRecipeSerializer(dish).data, status=status.HTTP_201_CREATED)
        model.objects.filter(user=request.user, dish=dish).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        """Фильтрация по автору, наличию в избранном или корзине."""
        qs = super().get_queryset()
        params = self.request.query_params

        if author := params.get("author"):
            qs = qs.filter(creator_id=author)

        if (
            params.get("is_in_shopping_cart") == "1"
            and self.request.user.is_authenticated
        ):
            qs = qs.filter(shoppingcarts__user=self.request.user)

        if (
            params.get("is_favorited") == "1"
            and self.request.user.is_authenticated
        ):
            qs = qs.filter(favorites__user=self.request.user)

        return qs

    def perform_create(self, serializer):
        """Устанавливает текущего пользователя автором рецепта."""
        serializer.save(creator=self.request.user)

    @action(detail=True, methods=["post", "delete"], url_path="favorite")
    def favorite(self, request, pk=None):
        """Добавление/удаление рецепта в/из избранного."""
        dish = get_object_or_404(Dish, pk=pk)
        return self._toggle(request, dish, FavoriteRecipe)

    @action(detail=True, methods=["post", "delete"], url_path="shopping_cart")
    def shopping_cart(self, request, pk=None):
        """Добавление/удаление рецепта в/из корзины покупок."""
        dish = get_object_or_404(Dish, pk=pk)
        return self._toggle(request, dish, ShoppingCartRecipe)

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_link(self, request, pk=None):
        """Генерация короткой ссылки на рецепт."""
        short = request.build_absolute_uri(reverse("recipe-short-link", args=[pk]))
        return Response({"short-link": short})

    @action(detail=False, methods=["get"], url_path="download_shopping_cart")
    def download_shopping_cart(self, request):
        """Формирует и возвращает список покупок в виде текстового файла."""
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Только для авторизованных."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        totals = defaultdict(int)
        dish_titles = set()

        for item in request.user.shopping_cart_recipes.select_related("dish"):
            dish_titles.add(item.dish.title)
            for amt in item.dish.recipe_ingredients.select_related("ingredient"):
                key = (amt.ingredient.name, amt.ingredient.measurement_unit)
                totals[key] += amt.amount

        today = timezone.localdate().strftime("%d.%m.%Y")
        lines = [f"Список покупок на {today}:", "Продукты:"]

        for idx, ((name, unit), amount) in enumerate(sorted(totals.items()), 1):
            lines.append(f"{idx}. {name.capitalize()} ({unit}) — {amount}")

        lines.append("\nРецепты, для которых нужны эти продукты:")
        for idx, title in enumerate(sorted(dish_titles), 1):
            lines.append(f"{idx}. {title}")

        report_text = "\n".join(lines)
        return FileResponse(
            report_text,
            content_type="text/plain",
            filename="shopping_cart.txt",
        )


class UserViewSet(DjoserUserViewSet):
    """Расширенный UserViewSet: подписки, аватар, профиль."""

    queryset = CustomUser.objects.all()
    serializer_class = PublicUserSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = CustomPagination

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="me",
    )
    def me(self, request):
        """Возвращает данные текущего пользователя."""
        return Response(self.get_serializer(request.user).data)

    @action(detail=False, methods=["put", "delete"], url_path="me/avatar")
    def avatar(self, request):
        """Позволяет обновить или удалить аватар пользователя."""
        user = request.user
        if request.method == "PUT":
            ser = self.get_serializer(user, data=request.data, partial=True)
            ser.is_valid(raise_exception=True)
            ser.save()
            return Response({"avatar": ser.data["avatar"]})
        user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post", "delete"], url_path="subscribe")
    def subscribe(self, request, id=None):
        """Подписка или отписка на автора по ID."""
        author = get_object_or_404(CustomUser, pk=id)

        if author == request.user:
            raise ValidationError({"error": "Нельзя подписаться на себя"})

        if request.method == "POST":
            obj, created = Follow.objects.get_or_create(
                follower=request.user,
                following=author,
            )
            if not created:
                raise ValidationError({"error": "Уже подписаны"})
            return Response(
                {"user": obj.follower.username, "author": author.username},
                status=status.HTTP_201_CREATED,
            )

        Follow.objects.filter(follower=request.user, following=author).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="subscriptions")
    def subscriptions(self, request):
        """Список авторов, на которых подписан пользователь."""
        subs_qs = (
            request.user.following_set.select_related("following")
            if request.user.is_authenticated
            else Follow.objects.none()
        )

        paginator = PageNumberPagination()
        paginator.page_size = int(request.query_params.get("limit", 6))
        page = paginator.paginate_queryset(subs_qs, request)

        authors = [sub.following for sub in page]
        ser = SubscribedAuthorSerializer(
            authors,
            many=True,
            context={"request": request},
        )
        return paginator.get_paginated_response(ser.data)
