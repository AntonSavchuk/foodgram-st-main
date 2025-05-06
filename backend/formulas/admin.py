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
    list_display = ("name", "measurement_unit")
    search_fields = ("name",)
    list_filter = ("measurement_unit",)
    ordering = ["name"]


@admin.register(Dish)
class DishConfig(admin.ModelAdmin):
    list_display = ("id", "title", "creator", "count_in_favorites")
    search_fields = ("creator__email", "title", "creator__username")
    list_filter = ("created_at",)
    ordering = ["-id"]

    @admin.display(description="Добавлений в избранное")
    def count_in_favorites(self, obj):
        return obj.favorites.count()


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

@admin.register(ShoppingCartRecipe)
class CartConfig(admin.ModelAdmin):
    list_display = ("user", "dish")
    search_fields = ("dish__title", "user__email")
    list_filter = ("dish",)
    ordering = ["dish"]
