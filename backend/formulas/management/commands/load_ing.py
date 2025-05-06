import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from formulas.models import Ingredient


class Command(BaseCommand):
    help = 'Импортирует ингредиенты из JSON‑файла в базу данных'

    def handle(self, *args, **options):
        json_path = Path(settings.BASE_DIR) / 'data' / 'ingredients.json'

        if not json_path.exists():
            self.stderr.write(self.style.ERROR(f'Не найден файл: {json_path}'))
            return

        try:
            raw = json_path.read_text(encoding='utf-8')
            items = json.loads(raw)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Ошибка при чтении JSON: {e}'))
            return

        objs = [Ingredient(**data) for data in items]
        created = Ingredient.objects.bulk_create(objs)

        count = len(created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Загружено {count} ингредиентов."
            )
        )
