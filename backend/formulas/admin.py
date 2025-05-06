"""
    Регистрация моделей рецептов и ингредиентов в административной
    панели Django.
"""

from django.contrib import admin

from .models import (
    Ingredient,
    Dish,
    IngredientAmount,
    FavoriteRecipe,
    ShoppingCartRecipe,
)


@admin.register(Ingredient)
class IngredientConfig(admin.ModelAdmin):
    """Отображение модели ингредиентов в админке."""

    list_display = ("name", "measurement_unit")
    search_fields = ("name",)
    list_filter = ("measurement_unit",)
    ordering = ["name"]


@admin.register(Dish)
class DishConfig(admin.ModelAdmin):
    """Настройка отображения рецептов (Dish) в админке."""

    list_display = ("id", "title", "creator", "count_in_favorites")
    search_fields = ("creator__email", "title", "creator__username")
    list_filter = ("created_at",)
    ordering = ["-id"]

    @admin.display(description="Добавлений в избранное")
    def count_in_favorites(self, obj):
        """Количество добавлений рецепта в избранное."""
        return obj.favorites.count()


@admin.register(IngredientAmount)
class IngredientLinkConfig(admin.ModelAdmin):
    """Админ-интерфейс связей между ингредиентами и рецептами."""

    list_display = ("ingredient", "amount", "dish")
    search_fields = ("ingredient__name", "dish__title")
    list_filter = ("ingredient",)


@admin.register(FavoriteRecipe)
class FavoriteConfig(admin.ModelAdmin):
    """Настройка отображения избранных рецептов пользователя."""

    list_display = ("user", "dish")
    search_fields = ("user__username", "dish__title")
    list_filter = ("user",)
    ordering = ["user"]


@admin.register(ShoppingCartRecipe)
class CartConfig(admin.ModelAdmin):
    """Админ-панель для управления корзинами покупок пользователей."""

    list_display = ("user", "dish")
    search_fields = ("dish__title", "user__email")
    list_filter = ("dish",)
    ordering = ["dish"]
