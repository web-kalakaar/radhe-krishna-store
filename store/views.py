from django.shortcuts import render

from .models import Category, Product


def home(request):
    categories = Category.objects.all()
    products = Product.objects.filter(is_available=True)[:8]
    return render(
        request,
        "store/home.html",
        {"categories": categories, "products": products},
    )