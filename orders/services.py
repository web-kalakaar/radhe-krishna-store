from decimal import Decimal

from django.db import transaction
from django.db.models import F

from store.models import Product

from .models import Cart, Order, OrderItem


class CheckoutError(Exception):
    """The order could not be placed. The message is shown to the customer."""


def delivery_charge_for(subtotal):
    """Free delivery for now. Later: free above ₹400, otherwise ₹50."""
    return Decimal("0")


@transaction.atomic
def place_order(user, address):
    cart = Cart.objects.filter(user=user).first()
    items = list(cart.items.select_related("product")) if cart else []
    if not items:
        raise CheckoutError("Your cart is empty.")

    for item in items:
        if not item.product.is_available:
            raise CheckoutError(f"{item.product.name} is no longer available.")

    subtotal = sum((item.line_total for item in items), Decimal("0"))
    delivery_charge = delivery_charge_for(subtotal)

    order = Order.objects.create(
        user=user,
        full_name=address.full_name,
        mobile=user.profile.mobile,
        line1=address.line1,
        line2=address.line2,
        city=address.city,
        state=address.state,
        pincode=address.pincode,
        delivery_charge=delivery_charge,
        total=subtotal + delivery_charge,
    )

    for item in items:
        product = item.product
        # Reduce stock only if enough is left, in a single database step.
        updated = Product.objects.filter(
            pk=product.pk, stock__gte=item.quantity
        ).update(stock=F("stock") - item.quantity)
        if not updated:
            raise CheckoutError(
                f"Sorry, {product.name} just went out of stock. Please review your cart."
            )

        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            price=product.price,
            quantity=item.quantity,
        )

    cart.items.all().delete()
    return order
@transaction.atomic
def cancel_order(order):
    """Cancel a placed order and return its items to stock."""
    # Change the status only if the order is still "placed". Doing this in one
    # database step means two clicks (or two tabs) can never restore stock twice.
    changed = Order.objects.filter(pk=order.pk, status=Order.Status.PLACED).update(
        status=Order.Status.CANCELLED
    )
    if not changed:
        raise CheckoutError("This order can no longer be cancelled.")

    for item in order.items.all():
        if item.product_id:
            Product.objects.filter(pk=item.product_id).update(
                stock=F("stock") + item.quantity
            )

@transaction.atomic
def mark_delivered(order):
    """Mark a placed order as delivered."""
    changed = Order.objects.filter(pk=order.pk, status=Order.Status.PLACED).update(
        status=Order.Status.DELIVERED
    )
    if not changed:
        raise CheckoutError("Only an order that is still placed can be marked as delivered.")