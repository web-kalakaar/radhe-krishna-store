from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from orders.models import Order
from orders.services import CheckoutError, cancel_order, mark_delivered
from store.models import Product
from store.utils import paginate

from .decorators import staff_required
from .forms import DeliveryForm

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
@staff_required
def order_list(request):
    orders = Order.objects.prefetch_related("items")

    status = request.GET.get("status", "")
    if status in Order.Status.values:
        orders = orders.filter(status=status)
    else:
        status = ""

    page_obj, querystring = paginate(request, orders, per_page=15)
    return render(
        request,
        "dashboard/order_list.html",
        {
            "page_obj": page_obj,
            "querystring": querystring,
            "current_status": status,
            "statuses": Order.Status.choices,
        },
    )


@staff_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)

    if request.method == "POST":
        if order.status != Order.Status.PLACED:
            messages.error(
                request, "Delivery details can only be changed while the order is placed."
            )
            return redirect("dashboard:order_detail", pk=order.pk)

        form = DeliveryForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, "Delivery details saved.")
            return redirect("dashboard:order_detail", pk=order.pk)
    else:
        form = DeliveryForm(instance=order)

    return render(
        request, "dashboard/order_detail.html", {"order": order, "form": form}
    )


@staff_required
@require_POST
def order_deliver(request, pk):
    order = get_object_or_404(Order, pk=pk)
    try:
        mark_delivered(order)
    except CheckoutError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Order {order.order_number} marked as delivered.")
    return redirect("dashboard:order_detail", pk=order.pk)


@staff_required
@require_POST
def order_cancel(request, pk):
    order = get_object_or_404(Order, pk=pk)
    try:
        cancel_order(order)
    except CheckoutError as error:
        messages.error(request, str(error))
    else:
        messages.success(
            request,
            f"Order {order.order_number} cancelled. The items are back in stock.",
        )
    return redirect("dashboard:order_detail", pk=order.pk)