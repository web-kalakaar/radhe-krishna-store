from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from urllib.parse import urlencode

from django.urls import reverse
from accounts.models import Profile
from store.models import Product
from store.utils import paginate
from .forms import CheckoutForm, QuantityForm
from .models import Cart, CartItem, Order
from .services import CheckoutError, cancel_order, delivery_charge_for, place_order


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
        messages.warning(request, f"Only {available} of {item.product.name} available.")
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


@login_required
def checkout(request):
    cart = Cart.objects.filter(user=request.user).first()
    items = []
    if cart:
        items = list(
            cart.items.select_related("product").prefetch_related("product__images")
        )

    if not items:
        messages.info(request, "Your cart is empty.")
        return redirect("orders:cart")

    if any(item.has_stock_problem for item in items):
        messages.error(request, "Please fix the problems in your cart before checkout.")
        return redirect("orders:order_detail", pk=order.pk)

    profile = Profile.objects.filter(user=request.user).first()
    if profile is None:
        messages.warning(
            request, "Please add your mobile number before placing an order."
        )
        return redirect("accounts:profile")

    if settings.REQUIRE_MOBILE_VERIFICATION and not profile.is_mobile_verified:
        messages.warning(
            request, "Please verify your mobile number before placing your order."
        )
        verify_url = (
            reverse("accounts:verify_mobile")
            + "?"
            + urlencode({"next": reverse("orders:checkout")})
        )
        return redirect(verify_url)

    if not request.user.addresses.exists():
        messages.info(request, "Add a delivery address to continue.")
        return redirect("accounts:address_add")

    if request.method == "POST":
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                order = place_order(request.user, form.cleaned_data["address"])
            except CheckoutError as error:
                messages.error(request, str(error))
                return redirect("orders:cart")
            messages.success(
                request, f"Order {order.order_number} placed successfully!"
            )
            return redirect("orders:cart")  # replaced by a confirmation page next step
    else:
        form = CheckoutForm(user=request.user)

    subtotal = sum((item.line_total for item in items), Decimal("0"))
    delivery_charge = delivery_charge_for(subtotal)

    return render(
        request,
        "orders/checkout.html",
        {
            "form": form,
            "items": items,
            "profile": profile,
            "subtotal": subtotal,
            "delivery_charge": delivery_charge,
            "total": subtotal + delivery_charge,
        },
    )


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.prefetch_related("items"), pk=pk, user=request.user
    )
    return render(request, "orders/order_detail.html", {"order": order})


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items")
    page_obj, querystring = paginate(request, orders, per_page=10)
    return render(
        request,
        "orders/order_list.html",
        {"page_obj": page_obj, "querystring": querystring},
    )


@login_required
@require_POST
def cancel_order_view(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)

    try:
        cancel_order(order)
    except CheckoutError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"Order {order.order_number} has been cancelled.")

    return redirect("orders:order_detail", pk=order.pk)
