from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from orders.models import Order
from orders.services import CheckoutError, cancel_order, mark_delivered
from store.models import Category, Product, StockLog
from store.stock import StockError, adjust_stock, set_stock
from store.utils import paginate

from .decorators import staff_required
from .forms import DeliveryForm, ProductForm, ProductImageFormSet, StockAdjustForm

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
                request,
                "Delivery details can only be changed while the order is placed.",
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


@staff_required
def stock_list(request):
    products = Product.objects.select_related("category").order_by("name", "id")

    query = request.GET.get("q", "").strip()[:100]
    for word in query.split():
        products = products.filter(Q(name__icontains=word) | Q(brand__icontains=word))

    stock_filter = request.GET.get("filter", "")
    if stock_filter == "low":
        products = products.filter(stock__gt=0, stock__lte=LOW_STOCK_LIMIT)
    elif stock_filter == "out":
        products = products.filter(stock=0)
    else:
        stock_filter = ""

    page_obj, querystring = paginate(request, products, per_page=20)
    return render(
        request,
        "dashboard/stock_list.html",
        {
            "page_obj": page_obj,
            "querystring": querystring,
            "query": query,
            "stock_filter": stock_filter,
            "low_stock_limit": LOW_STOCK_LIMIT,
            "action_choices": StockAdjustForm.ACTION_CHOICES,
        },
    )


@staff_required
@require_POST
def stock_adjust(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = StockAdjustForm(request.POST)

    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = reverse("dashboard:stock_list")

    if not form.is_valid():
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
        return redirect(next_url)

    action = form.cleaned_data["action"]
    quantity = form.cleaned_data["quantity"]
    note = form.cleaned_data["note"]

    try:
        if action == "sold":
            new_stock = adjust_stock(
                product.pk, -quantity, StockLog.Reason.OFFLINE_SALE, note, request.user
            )
            messages.success(
                request,
                f"Recorded {quantity} sold offline: {product.name}. Stock is now {new_stock}.",
            )
        elif action == "restock":
            new_stock = adjust_stock(
                product.pk, quantity, StockLog.Reason.RESTOCK, note, request.user
            )
            messages.success(
                request,
                f"Added {quantity} to {product.name}. Stock is now {new_stock}.",
            )
        else:
            new_stock = set_stock(product.pk, quantity, note, request.user)
            messages.success(request, f"Stock of {product.name} is now {new_stock}.")
    except StockError:
        messages.error(
            request,
            f"Cannot subtract {quantity} from {product.name}: "
            "there is not enough stock.",
        )

    return redirect(next_url)


@staff_required
def stock_history(request):
    logs = StockLog.objects.select_related("product", "created_by")

    query = request.GET.get("q", "").strip()[:100]
    for word in query.split():
        logs = logs.filter(Q(product__name__icontains=word) | Q(note__icontains=word))

    reason = request.GET.get("reason", "")
    if reason in StockLog.Reason.values:
        logs = logs.filter(reason=reason)
    else:
        reason = ""

    page_obj, querystring = paginate(request, logs, per_page=25)
    return render(
        request,
        "dashboard/stock_history.html",
        {
            "page_obj": page_obj,
            "querystring": querystring,
            "query": query,
            "reason": reason,
            "reasons": StockLog.Reason.choices,
        },
    )


MIN_PHOTOS = 3


def warn_if_few_photos(request, product):
    count = product.images.count()
    if count < MIN_PHOTOS:
        messages.warning(
            request,
            f"{product.name} has only {count} photo{'s' if count != 1 else ''}. "
            f"Products with at least {MIN_PHOTOS} photos look better.",
        )


@staff_required
def product_list(request):

    products = Product.objects.select_related("category").annotate(
        image_count=Count("images")
    )

    query = request.GET.get("q", "").strip()[:100]
    for word in query.split():
        products = products.filter(Q(name__icontains=word) | Q(brand__icontains=word))

    category_id = request.GET.get("category", "")
    if category_id.isdigit():
        products = products.filter(category_id=category_id)
    else:
        category_id = ""

    availability = request.GET.get("availability", "")
    if availability == "available":
        products = products.filter(is_available=True)
    elif availability == "hidden":
        products = products.filter(is_available=False)
    else:
        availability = ""

    page_obj, querystring = paginate(request, products, per_page=20)
    return render(
        request,
        "dashboard/product_list.html",
        {
            "page_obj": page_obj,
            "querystring": querystring,
            "query": query,
            "category_id": category_id,
            "availability": availability,
            "categories": Category.objects.all(),
        },
    )


@staff_required
def product_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        image_formset = ProductImageFormSet(request.POST, request.FILES)
        form_ok = form.is_valid()
        photos_ok = image_formset.is_valid()

        if form_ok and photos_ok:
            with transaction.atomic():
                product = form.save()
                image_formset.instance = product
                image_formset.save()
                if product.stock:
                    StockLog.objects.create(
                        product=product,
                        change=product.stock,
                        stock_after=product.stock,
                        reason=StockLog.Reason.RESTOCK,
                        note="Initial stock",
                        created_by=request.user,
                    )
            messages.success(request, f"{product.name} has been added.")
            warn_if_few_photos(request, product)
            return redirect("dashboard:product_list")
    else:
        form = ProductForm()
        image_formset = ProductImageFormSet()

    return render(
        request,
        "dashboard/product_form.html",
        {
            "form": form,
            "image_formset": image_formset,
            "title": "Add product",
            "product": None,
        },
    )


@staff_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        image_formset = ProductImageFormSet(
            request.POST, request.FILES, instance=product
        )
        form_ok = form.is_valid()
        photos_ok = image_formset.is_valid()

        if form_ok and photos_ok:
            with transaction.atomic():
                product = form.save()
                image_formset.save()
            messages.success(request, f"{product.name} has been updated.")
            warn_if_few_photos(request, product)
            return redirect("dashboard:product_list")
    else:
        form = ProductForm(instance=product)
        image_formset = ProductImageFormSet(instance=product)

    return render(
        request,
        "dashboard/product_form.html",
        {
            "form": form,
            "image_formset": image_formset,
            "title": "Edit product",
            "product": product,
        },
    )
