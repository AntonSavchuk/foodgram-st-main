from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from django.db.models import Count

from .models import (
    UserAccount,
    Follow,
    Ingredient,
    Dish,
    IngredientAmount,
    FavoriteRecipe,
    ShoppingCart,
)


@admin.register(UserAccount)
class UserPanelAdmin(UserAdmin):
    list_display = (
        'id', 'username', 'full_name', 'email', 'avatar_tag',
        'recipes_count', 'subscriptions_count', 'subscribers_count',
    )
    search_fields = ('email', 'username', 'first_name', 'last_name')
    list_filter = ('is_active',)
    ordering = ('id',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            recipes_count=Count('recipes', distinct=True),
            subscriptions_count=Count('following_set', distinct=True),
            subscribers_count=Count('followers_set', distinct=True),
        )

    @admin.display(description="ФИО")
    def full_name(self, user):
        return f"{user.first_name} {user.last_name}".strip()

    @admin.display(description="Аватар")
    def avatar_tag(self, user):
        if user.profile_picture:
            return f'<img src="{user.profile_picture.url}" width="50" height="50" style="border-radius: 4px;" />'
        return "—"

    @admin.display(description="Рецептов")
    def recipes_count(self, user):
        return user.recipes_count

    @admin.display(description="Подписок")
    def subscriptions_count(self, user):
        return user.subscriptions_count

    @admin.display(description="Подписчиков")
    def subscribers_count(self, user):
        return user.subscribers_count


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following')
    search_fields = ('follower__email', 'following__email')
    list_filter = ('follower',)


@admin.register(Ingredient)
class IngredientConfig(admin.ModelAdmin):
    list_display = ("name", "measurement_unit", "recipes_count")
    search_fields = ("name", "measurement_unit")
    list_filter = ("measurement_unit",)
    ordering = ["name"]

    @admin.display(description="Рецептов")
    def recipes_count(self, ingredient):
        return ingredient.recipe_ingredients.count()


@admin.register(Dish)
class DishConfig(admin.ModelAdmin):
    list_display = (
        "id", "title", "cook_time", "creator", "count_in_favorites",
        "display_ingredients", "display_image"
    )
    search_fields = ("creator__email", "title", "creator__username")
    list_filter = ("creator",)
    ordering = ["-id"]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(count=Count("favorites"))

    @admin.display(description="В избранном")
    def count_in_favorites(self, recipe):
        return recipe.favorites.count()

    @admin.display(description="Продукты")
    def display_ingredients(self, recipe):
        ingredients = recipe.recipe_ingredients.select_related("ingredient")
        return mark_safe("<br>".join(
            f"{ia.ingredient.name} — {ia.amount} {ia.ingredient.measurement_unit}" for ia in ingredients
        ))

    @admin.display(description="Изображение")
    def display_image(self, recipe):
        if recipe.image:
            return mark_safe(f'<img src="{recipe.image.url}" width="100" height="100" />')
        return "—"


@admin.register(IngredientAmount)
class IngredientLinkConfig(admin.ModelAdmin):
    list_display = ("ingredient", "amount", "dish")
    search_fields = ("ingredient__name", "dish__title")
    list_filter = ("ingredient",)


@admin.register(FavoriteRecipe)
class FavoriteConfig(admin.ModelAdmin):
    list_display = ("user", "dish")
    search_fields = ("user__username", "dish__title")
    list_filter = ("user",)
    ordering = ["user"]


@admin.register(ShoppingCart)
class CartConfig(admin.ModelAdmin):
    list_display = ("user", "dish")
    search_fields = ("dish__title", "user__email")
    list_filter = ("dish",)
    ordering = ["dish"]
