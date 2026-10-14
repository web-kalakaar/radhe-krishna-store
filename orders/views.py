from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from store.models import Product

from .forms import QuantityForm
from .models import Cart, CartItem


@login_required
def cart_detail(request):
    cart = Cart.objects.filter(user=request.user).first()
    items = []
    if cart:
        items = list(
            cart.items.select_related("product").prefetch_related("product__images")
        )

    total = sum((item.line_total for item in items), Decimal("0"))
    has_problems = any(item.has_stock_problem for item in items)

    return render(
        request,
        "orders/cart.html",
        {"items": items, "total": total, "has_problems": has_problems},
    )


@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_available=True)

    if product.stock < 1:
        messages.error(request, f"Sorry, {product.name} is out of stock.")
        return redirect("store:product_detail", slug=product.slug)

    cart, _ = Cart.objects.get_or_create(user=request.user)

    with transaction.atomic():
        item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            if item.quantity >= product.stock:
                messages.warning(
                    request,
                    f"Only {product.stock} of {product.name} available, "
                    "and all of them are already in your cart.",
                )
                return redirect("store:product_detail", slug=product.slug)
            item.quantity += 1
            item.save()

    messages.success(
        request,
        f"{product.name} added to your cart. You now have {item.quantity} in your cart.",
    )
    return redirect("store:product_detail", slug=product.slug)


@login_required
@require_POST
def update_cart_item(request, item_id):
    item = get_object_or_404(
        CartItem.objects.select_related("product"),
        pk=item_id,
        cart__user=request.user,
    )
    form = QuantityForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Enter a quantity between 1 and 99.")
        return redirect("orders:cart")

    quantity = form.cleaned_data["quantity"]
    available = item.product.stock

    if quantity > available:
        messages.warning(
            request, f"Only {available} of {item.product.name} available."
        )
        quantity = available

    if quantity >= 1:
        item.quantity = quantity
        item.save(update_fields=["quantity"])
        messages.success(request, "Cart updated.")

    return redirect("orders:cart")


@login_required
@require_POST
def remove_cart_item(request, item_id):
    item = get_object_or_404(
        CartItem.objects.select_related("product"),
        pk=item_id,
        cart__user=request.user,
    )
    name = item.product.name
    item.delete()
    messages.success(request, f"{name} removed from your cart.")
    return redirect("orders:cart")