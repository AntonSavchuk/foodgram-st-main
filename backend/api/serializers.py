"""Сериализаторы для API-приложения foodgram."""

from django.core.validators import MinValueValidator
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from formulas.models import (
    UserAccount,
    Follow,
    Ingredient,
    Dish,
    IngredientAmount,
    FavoriteRecipe,
    ShoppingCart,
)


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ингредиента."""
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class IngredientAmountSerializer(serializers.ModelSerializer):
    """Сериализатор количества ингредиента в рецепте (универсальный)."""
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source="ingredient",
    )
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(source="ingredient.measurement_unit")
    amount = serializers.IntegerField(min_value=1)

    class Meta:
        model = IngredientAmount
        fields = ("id", "name", "measurement_unit", "amount")


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Краткое представление рецепта для подписок и списков."""

    class Meta:
        model = Dish
        fields = ("id", "title", "image", "cook_time")
        read_only_fields = fields


class PublicUserSerializer(DjoserUserSerializer):
    """Сериализатор пользователя с полем подписки."""
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = UserAccount
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
        )

    def get_is_subscribed(self, user):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and Follow.objects.filter(follower=request.user, following=user).exists()
        )

class DishReadSerializer(serializers.ModelSerializer):
    """Сериализатор рецепта для чтения."""
    creator = serializers.SlugRelatedField(
        slug_field="username",
        read_only=True,
    )
    ingredients = IngredientAmountSerializer(
        source="recipe_ingredients",
        many=True,
        read_only=True
    )
    image = Base64ImageField(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = (
            "id",
            "title",
            "description",
            "image",
            "creator",
            "cook_time",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
        )

    def get_is_favorited(self, dish):
        user = self.context["request"].user
        return (
            user.is_authenticated
            and FavoriteRecipe.objects.filter(user=user, dish=dish).exists()
        )

    def get_is_in_shopping_cart(self, dish):
        user = self.context["request"].user
        return (
            user.is_authenticated
            and ShoppingCart.objects.filter(user=user, dish=dish).exists()
        )


class SubscribedAuthorSerializer(PublicUserSerializer):
    """Сериализатор автора с рецептами и их количеством."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source="dish.count", read_only=True)

    class Meta(PublicUserSerializer.Meta):
        fields = (*PublicUserSerializer.Meta.fields, "recipes", "recipes_count")

    def get_recipes(self, author):
        request = self.context["request"]
        limit = int(request.GET.get("recipes_limit", 10**10))
        return ShortRecipeSerializer(author.dish.all()[:limit], many=True).data


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор рецепта для чтения."""
    author = PublicUserSerializer(source="creator", read_only=True)
    ingredients = IngredientAmountSerializer(
        source="recipe_ingredients",
        many=True,
        read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = (
            "id",
            "title",
            "description",
            "image",
            "creator",
            "cook_time",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
        )
        read_only_fields = fields

    def get_is_favorited(self, recipe):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and FavoriteRecipe.objects.filter(user=request.user, dish=recipe).exists()
        )

    def get_is_in_shopping_cart(self, recipe):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and ShoppingCart.objects.filter(user=request.user, dish=recipe).exists()
        )


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор рецепта для создания и редактирования."""
    cooking_time = serializers.IntegerField(source="cook_time", min_value=1)
    ingredients = IngredientAmountSerializer(source="recipe_ingredients", many=True)
    image = Base64ImageField()

    class Meta:
        model = Dish
        fields = (
            "id",
            "title",
            "description",
            "image",
            "cook_time",
            "recipe_ingredients",
        )

    @staticmethod
    def _bulk_save_ingredients(dish, items):
        IngredientAmount.objects.bulk_create(
            IngredientAmount(
                dish=dish,
                ingredient=item["ingredient"],
                amount=item["amount"],
            )
            for item in items
        )

    def create(self, validated_data):
        ingredients = validated_data.pop("recipe_ingredients", [])
        dish = super().create(validated_data)
        self._bulk_save_ingredients(dish, ingredients)
        return dish

    def update(self, instance, validated_data):
        ingredients = validated_data.pop("recipe_ingredients", [])
        instance.recipe_ingredients.all().delete()
        dish = super().update(instance, validated_data)
        self._bulk_save_ingredients(dish, ingredients)
        return dish
