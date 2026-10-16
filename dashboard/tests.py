from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Address, Profile
from orders.models import Cart, CartItem, Order
from orders.services import mark_delivered, place_order
from store.models import Category, Product, StockLog

User = get_user_model()
PASSWORD = "test-pass-123"


def management(prefix):
    """The hidden counters a formset needs. Here: no photo or feature rows."""
    return {
        f"{prefix}-TOTAL_FORMS": "0",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


class DashboardTestCase(TestCase):
    """An owner, a customer with one placed order, and two products.

    The lamp (stock 10) is for stock and product tests. The order is for the mug
    (stock 10 before the order, 9 after).
    """

    def setUp(self):
        self.owner = User.objects.create_user("owner", password=PASSWORD, is_staff=True)
        self.customer = User.objects.create_user("asha", password=PASSWORD)
        Profile.objects.create(
            user=self.customer, mobile="9876543210", is_mobile_verified=True
        )
        address = Address.objects.create(
            user=self.customer,
            full_name="Asha Sharma",
            line1="12 Main Road",
            city="Bharatpur",
            state="Rajasthan",
            pincode="321001",
        )

        self.category = Category.objects.create(name="Decor", slug="decor")
        self.lamp = Product.objects.create(
            category=self.category,
            name="Test Lamp",
            mrp=Decimal("1000"),
            discount_percent=25,
            stock=10,
        )
        self.mug = Product.objects.create(
            category=self.category,
            name="Test Mug",
            mrp=Decimal("500"),
            discount_percent=0,
            stock=10,
        )

        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(cart=cart, product=self.mug, quantity=1)
        self.order = place_order(self.customer, address)

    def refresh_products(self):
        self.lamp.refresh_from_db()
        self.mug.refresh_from_db()


class PermissionTests(DashboardTestCase):
    def page_urls(self):
        return [
            reverse("dashboard:overview"),
            reverse("dashboard:order_list"),
            reverse("dashboard:order_detail", args=[self.order.pk]),
            reverse("dashboard:stock_list"),
            reverse("dashboard:stock_history"),
            reverse("dashboard:product_list"),
            reverse("dashboard:product_create"),
            reverse("dashboard:product_edit", args=[self.lamp.pk]),
        ]

    def action_urls(self):
        return [
            reverse("dashboard:order_deliver", args=[self.order.pk]),
            reverse("dashboard:order_cancel", args=[self.order.pk]),
            reverse("dashboard:stock_adjust", args=[self.lamp.pk]),
        ]

    def test_visitors_are_sent_to_the_login_page(self):
        for url in self.page_urls() + self.action_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith(reverse("accounts:login")))

    def test_customers_are_refused_every_owner_page(self):
        self.client.force_login(self.customer)

        for url in self.page_urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_customers_cannot_use_the_owner_actions(self):
        self.client.force_login(self.customer)

        for url in self.action_urls():
            with self.subTest(url=url):
                response = self.client.post(url, {"action": "restock", "quantity": "5"})
                self.assertEqual(response.status_code, 403)

        self.order.refresh_from_db()
        self.refresh_products()
        self.assertEqual(self.order.status, Order.Status.PLACED)
        self.assertEqual(self.lamp.stock, 10)
        self.assertEqual(self.mug.stock, 9)

    def test_the_owner_can_open_every_page(self):
        self.client.force_login(self.owner)

        for url in self.page_urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


class OverviewTests(DashboardTestCase):
    def test_the_overview_counts_orders_and_stock_problems(self):
        Product.objects.create(
            category=self.category, name="Low", mrp=Decimal("100"), stock=3
        )
        Product.objects.create(
            category=self.category, name="Gone", mrp=Decimal("100"), stock=0
        )
        Product.objects.create(
            category=self.category,
            name="Hidden and gone",
            mrp=Decimal("100"),
            stock=0,
            is_available=False,
        )
        self.client.force_login(self.owner)

        response = self.client.get(reverse("dashboard:overview"))

        self.assertEqual(response.context["new_orders_count"], 1)
        self.assertEqual(response.context["low_stock_count"], 1)
        self.assertEqual(response.context["out_of_stock_count"], 1)  # hidden one ignored


class OwnerOrderTests(DashboardTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)
        self.detail_url = reverse("dashboard:order_detail", args=[self.order.pk])

    def test_delivery_details_are_saved(self):
        response = self.client.post(
            self.detail_url,
            {"delivery_boy_name": "Ramesh", "delivery_boy_mobile": "9812345678"},
        )

        self.assertRedirects(response, self.detail_url, fetch_redirect_response=False)
        self.order.refresh_from_db()
        self.assertEqual(self.order.delivery_boy_name, "Ramesh")
        self.assertEqual(self.order.delivery_boy_mobile, "9812345678")

    def test_a_mobile_without_a_name_is_refused(self):
        response = self.client.post(
            self.detail_url,
            {"delivery_boy_name": "", "delivery_boy_mobile": "9812345678"},
        )

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.delivery_boy_mobile, "")

    def test_delivery_details_cannot_change_after_delivery(self):
        mark_delivered(self.order)

        self.client.post(
            self.detail_url,
            {"delivery_boy_name": "Ramesh", "delivery_boy_mobile": "9812345678"},
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.delivery_boy_name, "")

    def test_the_owner_can_mark_an_order_delivered(self):
        url = reverse("dashboard:order_deliver", args=[self.order.pk])

        response = self.client.post(url)

        self.assertRedirects(response, self.detail_url, fetch_redirect_response=False)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.DELIVERED)

    def test_the_owner_cancelling_an_order_restores_the_stock(self):
        url = reverse("dashboard:order_cancel", args=[self.order.pk])

        self.client.post(url)

        self.order.refresh_from_db()
        self.refresh_products()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)
        self.assertEqual(self.mug.stock, 10)

    def test_a_delivered_order_cannot_be_cancelled_by_the_owner(self):
        mark_delivered(self.order)
        url = reverse("dashboard:order_cancel", args=[self.order.pk])

        self.client.post(url)

        self.order.refresh_from_db()
        self.refresh_products()
        self.assertEqual(self.order.status, Order.Status.DELIVERED)
        self.assertEqual(self.mug.stock, 9)

    def test_an_unknown_status_filter_is_ignored(self):
        response = self.client.get(reverse("dashboard:order_list") + "?status=hack")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 1)


class StockPageTests(DashboardTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)
        self.url = reverse("dashboard:stock_adjust", args=[self.lamp.pk])
        self.list_url = reverse("dashboard:stock_list")

    def lamp_logs(self):
        return StockLog.objects.filter(product=self.lamp)

    def test_an_offline_sale_subtracts_stock_and_logs_who_did_it(self):
        response = self.client.post(
            self.url, {"action": "sold", "quantity": "3", "note": "Sold in shop"}
        )

        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        self.refresh_products()
        self.assertEqual(self.lamp.stock, 7)
        log = self.lamp_logs().get()
        self.assertEqual(log.change, -3)
        self.assertEqual(log.reason, StockLog.Reason.OFFLINE_SALE)
        self.assertEqual(log.note, "Sold in shop")
        self.assertEqual(log.created_by, self.owner)

    def test_a_restock_adds_stock(self):
        self.client.post(self.url, {"action": "restock", "quantity": "5"})

        self.refresh_products()
        self.assertEqual(self.lamp.stock, 15)
        self.assertEqual(self.lamp_logs().get().reason, StockLog.Reason.RESTOCK)

    def test_setting_an_exact_count_logs_the_difference(self):
        self.client.post(self.url, {"action": "set", "quantity": "4"})

        self.refresh_products()
        self.assertEqual(self.lamp.stock, 4)
        log = self.lamp_logs().get()
        self.assertEqual(log.change, -6)
        self.assertEqual(log.reason, StockLog.Reason.CORRECTION)

    def test_setting_the_count_it_already_has_adds_no_history(self):
        self.client.post(self.url, {"action": "set", "quantity": "10"})

        self.assertEqual(self.lamp_logs().count(), 0)

    def test_selling_more_than_the_stock_is_refused(self):
        self.client.post(self.url, {"action": "sold", "quantity": "11"})

        self.refresh_products()
        self.assertEqual(self.lamp.stock, 10)
        self.assertEqual(self.lamp_logs().count(), 0)

    def test_a_sale_of_zero_is_refused(self):
        self.client.post(self.url, {"action": "sold", "quantity": "0"})

        self.refresh_products()
        self.assertEqual(self.lamp.stock, 10)
        self.assertEqual(self.lamp_logs().count(), 0)

    def test_the_owner_returns_to_the_page_they_came_from(self):
        response = self.client.post(
            self.url,
            {"action": "restock", "quantity": "1", "next": "/owner/stock/?q=lamp"},
        )

        self.assertRedirects(
            response, "/owner/stock/?q=lamp", fetch_redirect_response=False
        )

    def test_a_next_address_on_another_website_is_ignored(self):
        response = self.client.post(
            self.url,
            {"action": "restock", "quantity": "1", "next": "https://example.com/"},
        )

        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)


class ProductManagementTests(DashboardTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def product_data(self, **overrides):
        data = {
            "category": self.category.pk,
            "name": "New Lamp",
            "brand": "Glowly",
            "description": "A nice lamp.",
            "mrp": "1000",
            "discount_percent": "25",
            "stock": "5",
            "is_available": "on",
            **management("images"),
            **management("features"),
        }
        data.update(overrides)
        return data

    def test_the_owner_can_add_a_product(self):
        response = self.client.post(
            reverse("dashboard:product_create"), self.product_data(), follow=True
        )

        product = Product.objects.get(name="New Lamp")
        self.assertEqual(product.price, Decimal("750"))
        self.assertEqual(product.slug, "new-lamp")
        self.assertContains(response, "has been added")
        self.assertContains(response, "has only 0 photos")  # the fewer-than-3 warning

    def test_the_first_stock_of_a_new_product_is_logged(self):
        self.client.post(reverse("dashboard:product_create"), self.product_data())

        log = StockLog.objects.get(product__name="New Lamp")
        self.assertEqual(log.change, 5)
        self.assertEqual(log.note, "Initial stock")
        self.assertEqual(log.created_by, self.owner)

    def test_an_mrp_of_zero_is_refused(self):
        response = self.client.post(
            reverse("dashboard:product_create"), self.product_data(mrp="0")
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.filter(name="New Lamp").exists())

    def test_editing_cannot_change_the_stock(self):
        url = reverse("dashboard:product_edit", args=[self.lamp.pk])

        response = self.client.post(
            url,
            self.product_data(name="Renamed Lamp", discount_percent="50", stock="999"),
        )

        self.assertRedirects(
            response, reverse("dashboard:product_list"), fetch_redirect_response=False
        )
        self.lamp.refresh_from_db()
        self.assertEqual(self.lamp.stock, 10)
        self.assertEqual(self.lamp.name, "Renamed Lamp")
        self.assertEqual(self.lamp.price, Decimal("500"))
        self.assertEqual(self.lamp.slug, "test-lamp")  # the web address stays

    def test_unchecking_available_hides_the_product(self):
        url = reverse("dashboard:product_edit", args=[self.lamp.pk])
        data = self.product_data()
        del data["is_available"]

        self.client.post(url, data)

        self.lamp.refresh_from_db()
        self.assertFalse(self.lamp.is_available)

    def test_a_customer_cannot_add_a_product(self):
        self.client.force_login(self.customer)

        response = self.client.post(
            reverse("dashboard:product_create"), self.product_data()
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Product.objects.filter(name="New Lamp").exists())

    def test_unknown_filters_in_the_product_list_are_ignored(self):
        url = reverse("dashboard:product_list") + "?category=abc&availability=hack"

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)