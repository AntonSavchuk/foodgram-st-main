"""Настройка пользовательской пагинации для API."""

from rest_framework.pagination import PageNumberPagination


class PageNumberLimitPagination(PageNumberPagination):
    """Пагинация с параметром 'limit' для задания размера страницы.

    Атрибуты:
        page_size_query_param (str): Название GET-параметра для ограничения
        размера страницы.
        page_size (int): Значение размера страницы по умолчанию.
    """
    page_size_query_param = "limit"
    page_size = 6
