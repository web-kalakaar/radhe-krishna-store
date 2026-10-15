from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.conf import settings
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    brand = models.CharField(max_length=100, blank=True)
    description = models.TextField(
        blank=True, help_text="Add available sizes here if the product has sizes."
    )
    mrp = models.DecimalField(
        "MRP", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    discount_percent = models.PositiveSmallIntegerField(
        "discount (%)",
        default=0,
        validators=[MaxValueValidator(99)],
        help_text="Enter 0 for no discount.",
    )
    price = models.DecimalField(
        "selling price", max_digits=10, decimal_places=2, editable=False
    )
    stock = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(discount_percent__lte=99),
                name="product_discount_lte_99",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._make_unique_slug()
        self.price = self.calculate_price()
        super().save(*args, **kwargs)

    def _make_unique_slug(self):
        """Make a URL name from the product name, adding -2, -3 ... if it is taken."""
        base = slugify(self.name)[:200] or "product"
        slug, number = base, 2
        while Product.objects.filter(slug=slug).exists():
            slug = f"{base}-{number}"
            number += 1
        return slug
    
    def calculate_price(self):
        """Selling price = MRP minus discount, rounded to the nearest rupee."""
        factor = Decimal(100 - self.discount_percent) / Decimal(100)
        return (self.mrp * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    @property
    def in_stock(self):
        return self.is_available and self.stock > 0

    @property
    def main_image(self):
        """The first photo (lowest sort order), or None if there are no photos."""
        return self.images.first()


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Lower numbers come first. The first photo is the main one.",
    )

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.product.name} (image {self.pk})"

class ProductFeature(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="features"
    )
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=255)
    sort_order = models.PositiveSmallIntegerField(
        default=0, help_text="Lower numbers are shown first."
    )

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.name}: {self.value}"
    
class StockLog(models.Model):
    class Reason(models.TextChoices):
        ONLINE_ORDER = "online_order", "Online order"
        ORDER_CANCELLED = "order_cancelled", "Order cancelled"
        OFFLINE_SALE = "offline_sale", "Sold offline"
        RESTOCK = "restock", "Restocked"
        CORRECTION = "correction", "Stock count correction"

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="stock_logs"
    )
    change = models.IntegerField(help_text="Positive adds stock, negative removes it.")
    stock_after = models.PositiveIntegerField()
    reason = models.CharField(max_length=20, choices=Reason.choices)
    note = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(change=0), name="stocklog_change_not_zero"
            ),
        ]

    def __str__(self):
        return f"{self.product}: {self.change:+d} ({self.get_reason_display()})"