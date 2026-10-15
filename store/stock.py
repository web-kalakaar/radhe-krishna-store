from django.db import transaction
from django.db.models import F

from .models import Product, StockLog


class StockError(Exception):
    """The stock could not be changed."""


@transaction.atomic
def adjust_stock(product_id, delta, reason, note="", user=None):
    """Add `delta` to a product's stock (negative removes) and record it in the log.

    The only place in the project that changes stock. Returns the new stock.
    """
    if delta == 0:
        raise StockError("The change cannot be zero.")

    products = Product.objects.filter(pk=product_id)
    if delta < 0:
        products = products.filter(stock__gte=-delta)  # never go below zero

    if not products.update(stock=F("stock") + delta):
        raise StockError("Not enough stock, or the product does not exist.")

    new_stock = Product.objects.values_list("stock", flat=True).get(pk=product_id)
    StockLog.objects.create(
        product_id=product_id,
        change=delta,
        stock_after=new_stock,
        reason=reason,
        note=note,
        created_by=user,
    )
    return new_stock