from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Category, Product, StockLog
from .stock import StockError, adjust_stock


def make_product(category, **overrides):
    """Create a product with sensible defaults. Pass only what a test cares about."""
    values = {
        "category": category,
        "name": "Test Lamp",
        "mrp": Decimal("1000"),
        "discount_percent": 0,
        "stock": 10,
    }
    values.update(overrides)
    return Product.objects.create(**values)


class ProductPriceTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Decor", slug="decor")

    def test_price_equals_mrp_when_there_is_no_discount(self):
        product = make_product(self.category, mrp=Decimal("1000"), discount_percent=0)
        self.assertEqual(product.price, Decimal("1000"))

    def test_price_is_calculated_from_mrp_and_discount(self):
        product = make_product(self.category, mrp=Decimal("1000"), discount_percent=25)
        self.assertEqual(product.price, Decimal("750"))

    def test_price_is_rounded_to_a_whole_rupee(self):
        # 2999 minus 71% is 869.71, which rounds to 870.
        product = make_product(self.category, mrp=Decimal("2999"), discount_percent=71)
        self.assertEqual(product.price, Decimal("870"))

    def test_price_is_saved_in_the_database_and_follows_discount_changes(self):
        product = make_product(self.category, mrp=Decimal("1000"), discount_percent=25)
        product.discount_percent = 50
        product.save()
        product.refresh_from_db()
        self.assertEqual(product.price, Decimal("500"))

    def test_database_rejects_a_discount_of_100_percent_or_more(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_product(self.category, discount_percent=100)


class ProductSlugTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Decor", slug="decor")

    def test_slug_is_made_from_the_name(self):
        product = make_product(self.category, name="Wooden Photo Frame")
        self.assertEqual(product.slug, "wooden-photo-frame")

    def test_products_with_the_same_name_get_different_slugs(self):
        first = make_product(self.category, name="Test Lamp")
        second = make_product(self.category, name="Test Lamp")
        self.assertEqual(first.slug, "test-lamp")
        self.assertEqual(second.slug, "test-lamp-2")

    def test_slug_does_not_change_when_the_name_changes(self):
        product = make_product(self.category, name="Test Lamp")
        product.name = "Brand New Name"
        product.save()
        product.refresh_from_db()
        self.assertEqual(product.slug, "test-lamp")


class ProductStockStatusTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Decor", slug="decor")

    def test_product_with_stock_is_in_stock(self):
        self.assertTrue(make_product(self.category, stock=3).in_stock)

    def test_product_with_zero_stock_is_not_in_stock(self):
        self.assertFalse(make_product(self.category, stock=0).in_stock)

    def test_hidden_product_is_not_in_stock_even_with_stock(self):
        product = make_product(self.category, stock=5, is_available=False)
        self.assertFalse(product.in_stock)


class AdjustStockTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Decor", slug="decor")
        self.product = make_product(self.category, stock=10)

    def test_adding_stock_updates_the_product_and_writes_a_log(self):
        new_stock = adjust_stock(
            self.product.pk, 5, StockLog.Reason.RESTOCK, note="New delivery"
        )

        self.assertEqual(new_stock, 15)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 15)

        log = StockLog.objects.get()
        self.assertEqual(log.change, 5)
        self.assertEqual(log.stock_after, 15)
        self.assertEqual(log.reason, StockLog.Reason.RESTOCK)
        self.assertEqual(log.note, "New delivery")

    def test_subtracting_stock_updates_the_product_and_writes_a_log(self):
        adjust_stock(self.product.pk, -4, StockLog.Reason.OFFLINE_SALE)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 6)
        self.assertEqual(StockLog.objects.get().change, -4)

    def test_stock_cannot_go_below_zero(self):
        with self.assertRaises(StockError):
            adjust_stock(self.product.pk, -11, StockLog.Reason.OFFLINE_SALE)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)
        self.assertEqual(StockLog.objects.count(), 0)

    def test_a_change_of_zero_is_refused(self):
        with self.assertRaises(StockError):
            adjust_stock(self.product.pk, 0, StockLog.Reason.CORRECTION)
        self.assertEqual(StockLog.objects.count(), 0)

    def test_unknown_product_is_refused(self):
        with self.assertRaises(StockError):
            adjust_stock(999999, 1, StockLog.Reason.RESTOCK)
        self.assertEqual(StockLog.objects.count(), 0)