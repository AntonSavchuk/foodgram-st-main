"""Сериализаторы для API-приложения foodgram."""

from django.core.validators import MinValueValidator
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from formulas.models import (
    Ingredient,
    Dish,
    IngredientAmount,
    FavoriteRecipe,
    ShoppingCartRecipe,
)
from users.models import Follow


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ингредиента."""

    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class IngredientAmountSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения количества ингредиентов в рецепте."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source="ingredient",
    )
    name = serializers.CharField(
        source="ingredient.name",
        read_only=True,
    )
    measurement_unit = serializers.CharField(
        source="ingredient.measurement_unit",
        read_only=True,
    )
    amount = serializers.IntegerField(
        validators=[MinValueValidator(1, "Минимум 1")]
    )

    class Meta:
        model = IngredientAmount
        fields = ("id", "name", "measurement_unit", "amount")


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Краткое представление рецепта для подписок и списков."""

    name = serializers.CharField(source="title")
    cooking_time = serializers.IntegerField(source="cook_time")

    class Meta:
        model = Dish
        fields = ("id", "name", "image", "cooking_time")


class PublicUserSerializer(DjoserUserSerializer):
    """Сериализатор пользователя с полем подписки и аватаром."""

    avatar = Base64ImageField(required=False)
    is_subscribed = serializers.SerializerMethodField()

    class Meta(DjoserUserSerializer.Meta):
        fields = (*DjoserUserSerializer.Meta.fields, "avatar", "is_subscribed")

    def get_is_subscribed(self, obj):
        """Возвращает True, если текущий пользователь подписан на obj."""
        req = self.context.get("request")
        return (
            req
            and req.user.is_authenticated
            and Follow.objects.filter(
                follower=req.user,
                following=obj,
            ).exists()
        )


class SubscribedAuthorSerializer(PublicUserSerializer):
    """Сериализатор автора с рецептами и их количеством."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source="recipes.count",
        read_only=True,
    )

    class Meta(PublicUserSerializer.Meta):
        fields = (
            *PublicUserSerializer.Meta.fields,
            "recipes",
            "recipes_count",
        )

    def get_recipes(self, author):
        """Возвращает список рецептов автора, ограниченный параметром limit."""
        limit = int(
            self.context["request"].query_params.get("recipes_limit", 10**10)
        )
        qs = author.recipes.all()[:limit]
        return ShortRecipeSerializer(qs, many=True).data


class RecipeSerializer(serializers.ModelSerializer):
    """Полный сериализатор рецепта с ингредиентами, автором и статусами."""

    name = serializers.CharField(source="title")
    text = serializers.CharField(source="description")
    cooking_time = serializers.IntegerField(source="cook_time")
    author = PublicUserSerializer(source="creator", read_only=True)
    ingredients = IngredientAmountSerializer(
        source="recipe_ingredients",
        many=True,
    )
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = (
            "id",
            "name",
            "text",
            "image",
            "author",
            "cooking_time",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
        )

    @staticmethod
    def _bulk_save_ingredients(dish, items):
        """Сохраняет список ингредиентов в связанную таблицу через bulk_create."""
        IngredientAmount.objects.bulk_create(
            IngredientAmount(
                dish=dish,
                ingredient=item["ingredient"],
                amount=item["amount"],
            )
            for item in items
        )

    def _flag(self, model, dish):
        """Универсальная проверка: находится ли рецепт в указанной модели."""
        req = self.context.get("request")
        return (
            req
            and req.user.is_authenticated
            and model.objects.filter(user=req.user, dish=dish).exists()
        )

    def get_is_favorited(self, obj):
        """Возвращает True, если рецепт в избранном у пользователя."""
        return self._flag(FavoriteRecipe, obj)

    def get_is_in_shopping_cart(self, obj):
        """Возвращает True, если рецепт в корзине пользователя."""
        return self._flag(ShoppingCartRecipe, obj)

    def create(self, validated_data):
        """Создаёт новый рецепт с вложенными ингредиентами."""
        ingredients = validated_data.pop("recipe_ingredients", [])
        dish = Dish.objects.create(**validated_data)
        self._bulk_save_ingredients(dish, ingredients)
        return dish

    def update(self, instance, validated_data):
        """Обновляет рецепт и его ингредиенты."""
        ingredients = validated_data.pop("recipe_ingredients", [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        instance.recipe_ingredients.all().delete()
        self._bulk_save_ingredients(instance, ingredients)
        return instance
