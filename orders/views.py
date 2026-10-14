from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from store.models import Product

from .models import Cart, CartItem


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
