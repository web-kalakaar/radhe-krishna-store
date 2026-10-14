from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from accounts.models import mobile_validator

class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user}"

    @property
    def total(self):
        return sum((item.line_total for item in self.items.all()), Decimal("0"))

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "store.Product", on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["added_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"], name="unique_product_per_cart"
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="cartitem_quantity_gte_1",
            ),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product}"

    @property
    def line_total(self):
        return self.product.price * self.quantity
    @property
    def has_stock_problem(self):
        """True if the product is hidden, sold out, or the cart holds more than the stock."""
        return not self.product.in_stock or self.quantity > self.product.stock
    
class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = "placed", "Order placed"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "Cash on Delivery"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLACED
    )
    payment_method = models.CharField(
        max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.COD
    )

    # Delivery details, copied from the customer's profile and address
    # at the moment the order is placed.
    full_name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=10)
    line1 = models.CharField(max_length=200)
    line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6)

    delivery_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    delivery_boy_name = models.CharField(max_length=100, blank=True)
    delivery_boy_mobile = models.CharField(
        max_length=10, blank=True, validators=[mobile_validator]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number

    @property
    def order_number(self):
        return f"RK{self.pk:05d}"

    @property
    def subtotal(self):
        return self.total - self.delivery_charge

    @property
    def is_cancellable(self):
        return self.status == self.Status.PLACED


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "store.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    product_name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"

    @property
    def line_total(self):
        return self.price * self.quantity