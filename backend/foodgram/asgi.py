"""ASGI-конфигурация проекта: точка входа для асинхронных серверов
(Daphne, Uvicorn и др.)."""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodgram.settings')

application = get_asgi_application()
