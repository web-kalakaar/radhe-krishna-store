from django.shortcuts import render

from orders.models import Order
from store.models import Product

from .decorators import staff_required

LOW_STOCK_LIMIT = 5


@staff_required
def overview(request):
    available = Product.objects.filter(is_available=True)
    new_orders = Order.objects.filter(status=Order.Status.PLACED)

    return render(
        request,
        "dashboard/overview.html",
        {
            "new_orders_count": new_orders.count(),
            "recent_orders": new_orders.select_related("user")[:5],
            "out_of_stock_count": available.filter(stock=0).count(),
            "low_stock_count": available.filter(
                stock__gt=0, stock__lte=LOW_STOCK_LIMIT
            ).count(),
            "low_stock_limit": LOW_STOCK_LIMIT,
            "attention_products": available.filter(stock__lte=LOW_STOCK_LIMIT).order_by(
                "stock", "name"
            )[:10],
        },
    )