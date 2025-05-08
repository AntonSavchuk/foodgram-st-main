"""Модели приложения 'formulas': рецепты, ингредиенты, корзина и избранное."""

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models


class UserAccount(AbstractUser):
    email = models.EmailField(
        unique=True,
        max_length=254,
        verbose_name='Электронная почта'
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[RegexValidator(regex=r'^[\w.@+-]+$')],
        verbose_name='Логин'
    )
    first_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name='Фамилия'
    )
    profile_picture = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Фотография профиля'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'password']

    class Meta:
        verbose_name = 'Аккаунт'
        verbose_name_plural = 'Аккаунты'
        ordering = ('email',)

    def __str__(self):
        return self.username


class Follow(models.Model):
    follower = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name='following_set',
        verbose_name='Кто подписан'
    )
    following = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name='followers_set',
        verbose_name='На кого подписан'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['follower', 'following'],
                name='unique_follow_relation'
            )
        ]
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f"{self.follower} → {self.following}"


class Ingredient(models.Model):
    name = models.CharField(
        max_length=128,
        verbose_name="Название",
    )
    measurement_unit = models.CharField(
        max_length=64,
        verbose_name="Ед. изм.",
    )

    class Meta:
        ordering = ("name",)
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        constraints = [
            models.UniqueConstraint(
                fields=("name", "measurement_unit"),
                name="unique_ingredient_name_unit",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.measurement_unit})"


class Dish(models.Model):
    title = models.CharField(
        max_length=256,
        verbose_name="Название рецепта",
    )
    description = models.TextField(
        verbose_name="Описание",
    )
    image = models.ImageField(
        upload_to="dishes/images/",
        verbose_name="Фото",
        blank=True,
        null=True,
    )
    creator = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        verbose_name="Автор",
    )
    cook_time = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Время приготовления, мин",
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through="IngredientAmount",
        verbose_name="Ингредиенты",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата публикации",
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
        default_related_name = "dishes"

    def __str__(self):
        return f"{self.title} (id={self.id})"


class IngredientAmount(models.Model):
    dish = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        verbose_name="Рецепт",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name="Ингредиент",
    )
    amount = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Количество",
    )

    class Meta:
        verbose_name = "Ингредиент рецепта"
        verbose_name_plural = "Ингредиенты рецептов"
        constraints = [
            models.UniqueConstraint(
                fields=("dish", "ingredient"),
                name="unique_dish_ingredient",
            )
        ]
        default_related_name = "recipe_ingredients"

    def __str__(self):
        return (
            f"{self.ingredient.name} — {self.amount} "
            f"{self.ingredient.measurement_unit} для «{self.dish.title}»"
        )


class UserRecipeRelation(models.Model):
    user = models.ForeignKey(
        UserAccount,
        on_delete=models.CASCADE,
        related_name="%(class)s_user_set",
        verbose_name="Пользователь",
    )
    dish = models.ForeignKey(
        Dish,
        on_delete=models.CASCADE,
        related_name="%(class)s_dish_set",
        verbose_name="Рецепт",
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=("user", "dish"),
                name="%(class)s_unique_user_dish",
            )
        ]

    def __str__(self):
        return f"{self.user} → {self.dish}"


class FavoriteRecipe(UserRecipeRelation):
    class Meta(UserRecipeRelation.Meta):
        verbose_name = "Избранный рецепт"
        verbose_name_plural = "Избранные рецепты"


class ShoppingCart(UserRecipeRelation):
    class Meta(UserRecipeRelation.Meta):
        verbose_name = "Корзина покупок"
        verbose_name_plural = "Корзины покупок"
