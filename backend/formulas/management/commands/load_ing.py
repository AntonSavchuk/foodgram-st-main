"""Команда Django для загрузки ингредиентов из JSON-файла в базу данных."""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from formulas.models import Ingredient


class Command(BaseCommand):
    help = 'Импортирует ингредиенты из JSON‑файла в базу данных'

    def handle(self, *args, **options):
        try:
            json_path = Path(settings.BASE_DIR) / 'data' / 'ingredients.json'
            with json_path.open(encoding='utf-8') as file:
                data = json.load(file)

            unique = {
                (item['name'].strip().lower(), item['measurement_unit'].strip().lower()): item
                for item in data
            }.values()

            created = Ingredient.objects.bulk_create(
                [Ingredient(**item) for item in unique],
                ignore_conflicts=True
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Успешно загружено {len(created)} ингредиентов из файла: {json_path.name}"
                )
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(
                f"Ошибка при загрузке файла {json_path.name}: {e}"
            ))
