"""Конфигурация приложения 'formulas', отвечающего за рецепты и ингредиенты."""

from django.apps import AppConfig


class FormulasConfig(AppConfig):
    """Настройка приложения 'formulas'."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "formulas"
