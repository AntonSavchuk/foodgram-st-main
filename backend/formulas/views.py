from django.shortcuts import get_object_or_404, redirect
from formulas.models import Dish


def short_link_view(request, pk):
    dish = get_object_or_404(Dish, pk=pk)
    return redirect(f"/recipes/{dish.pk}/")
