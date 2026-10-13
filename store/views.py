from django.shortcuts import get_object_or_404, render
from .forms import ProductFilterForm
from .models import Category, Product
from django.db.models import Q
from .utils import paginate

def home(request):
    available = Product.objects.filter(is_available=True).prefetch_related("images")
    return render(
        request,
        "store/home.html",
        {
            "categories": Category.objects.all(),
            "featured_products": available.filter(is_featured=True)[:8],
            "new_products": available[:8],
        },
    )


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.filter(is_available=True).prefetch_related("images")

    form = ProductFilterForm(request.GET)
    products = form.filter_queryset(products)
    page_obj, querystring = paginate(request, products)

    return render(
        request,
        "store/category_detail.html",
        {
            "category": category,
            "page_obj": page_obj,
            "querystring": querystring,
            "form": form,
        },
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
def search(request):
    query = request.GET.get("q", "").strip()[:100]
    products = Product.objects.none()

    if query:
        products = Product.objects.filter(is_available=True)
        for word in query.split():
            products = products.filter(
                Q(name__icontains=word)
                | Q(brand__icontains=word)
                | Q(category__name__icontains=word)
            )
        products = products.prefetch_related("images")

    page_obj, querystring = paginate(request, products)

    return render(
        request,
        "store/search.html",
        {"query": query, "page_obj": page_obj, "querystring": querystring},
    )