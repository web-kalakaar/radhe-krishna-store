from django.shortcuts import get_object_or_404, render
from .forms import ProductFilterForm
from .models import Category, Product


def home(request):
    categories = Category.objects.all()
    products = Product.objects.filter(is_available=True).prefetch_related("images")[:8]
    return render(
        request,
        "store/home.html",
        {"categories": categories, "products": products},
    )


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.filter(is_available=True).prefetch_related("images")

    form = ProductFilterForm(request.GET)
    products = form.filter_queryset(products)

    return render(
        request,
        "store/category_detail.html",
        {"category": category, "products": products, "form": form},
    )
    
def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related(
            "images", "features"
        ),
        slug=slug,
        is_available=True,
    )
    return render(request, "store/product_detail.html", {"product": product})