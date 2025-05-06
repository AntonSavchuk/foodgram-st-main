from django.core.validators import MinValueValidator
from djoser.serializers import UserSerializer as BaseUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from formulas.models import (
    Ingredient,
    Dish,
    IngredientAmount,
    FavoriteRecipe,
    ShoppingCartRecipe,
)
from users.models import CustomUser


class IngredientDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class IngredientWithAmountSerializer(serializers.ModelSerializer):
    ingredient_id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source="ingredient"
    )
    ingredient_name = serializers.ReadOnlyField(source="ingredient.name")
    unit = serializers.ReadOnlyField(source="ingredient.measurement_unit")
    amount = serializers.IntegerField(
        validators=[MinValueValidator(1, "Минимальное количество — 1")]
    )

    class Meta:
        model = IngredientAmount
        fields = ("ingredient_id", "ingredient_name", "unit", "amount")


class MiniDishSerializer(serializers.ModelSerializer):
    dish_name = serializers.CharField(source="title")
    time_to_cook = serializers.IntegerField(source="cook_time")

    class Meta:
        model = Dish
        fields = ("id", "dish_name", "image", "time_to_cook")


class ExtendedUserSerializer(BaseUserSerializer):
    profile_picture = Base64ImageField(required=False)
    subscribed = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        fields = (*BaseUserSerializer.Meta.fields, "profile_picture", "subscribed")

    def get_subscribed(self, user_obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return CustomUser.objects.filter(
                subscriber=request.user,
                author=user_obj
            ).exists()
        return False


class AuthorWithDishesSerializer(ExtendedUserSerializer):
    recipes = serializers.SerializerMethodField()
    total_recipes = serializers.IntegerField(
        source="recipes.count",
        read_only=True
    )

    class Meta(ExtendedUserSerializer.Meta):
        fields = (*ExtendedUserSerializer.Meta.fields, "recipes", "total_recipes")

    def get_recipes(self, author_obj):
        limit = int(self.context["request"].query_params.get("recipes_limit", 100000))
        dishes = author_obj.recipes.all()[:limit]
        return MiniDishSerializer(dishes, many=True).data


class FullRecipeSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="title")
    description = serializers.CharField(source="description")
    time = serializers.IntegerField(source="cook_time")
    image = Base64ImageField()

    creator = ExtendedUserSerializer(source="creator", read_only=True)
    components = IngredientWithAmountSerializer(
        source="recipe_ingredients",
        many=True
    )
    favorited = serializers.SerializerMethodField()
    in_cart = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = (
            "id", "title", "description", "image", "creator", "time",
            "components", "favorited", "in_cart"
        )

    def _save_ingredients(self, dish, ingredient_data):
        IngredientAmount.objects.bulk_create([
            IngredientAmount(
                dish=dish,
                ingredient=item["ingredient"],
                amount=item["amount"]
            )
            for item in ingredient_data
        ])

    def _is_related(self, relation_model, dish):
        req = self.context.get("request")
        return (
            req
            and req.user.is_authenticated
            and relation_model.objects.filter(user=req.user, dish=dish).exists()
        )

    def get_favorited(self, obj):
        return self._is_related(FavoriteRecipe, obj)

    def get_in_cart(self, obj):
        return self._is_related(ShoppingCartRecipe, obj)

    def create(self, validated_data):
        ingredients = validated_data.pop("recipe_ingredients", [])
        new_dish = Dish.objects.create(**validated_data)
        self._save_ingredients(new_dish, ingredients)
        return new_dish

    def update(self, instance, validated_data):
        new_ingredients = validated_data.pop("recipe_ingredients", [])
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        instance.recipe_ingredients.all().delete()
        self._save_ingredients(instance, new_ingredients)
        return instance
