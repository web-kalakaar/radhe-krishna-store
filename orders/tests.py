from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Address, Profile
from store.models import Category, Product, StockLog

from .models import Cart, CartItem, Order
from .services import CheckoutError, cancel_order, mark_delivered, place_order

User = get_user_model()


def make_customer(username="asha", verified=True):
    user = User.objects.create_user(username=username, password="test-pass-123")
    Profile.objects.create(user=user, mobile="9876543210", is_mobile_verified=verified)
    address = Address.objects.create(
        user=user,
        full_name="Asha Sharma",
        line1="12 Main Road",
        city="Bharatpur",
        state="Rajasthan",
        pincode="321001",
    )
    return user, address


def make_product(category, name, mrp, discount, stock):
    return Product.objects.create(
        category=category,
        name=name,
        mrp=Decimal(mrp),
        discount_percent=discount,
        stock=stock,
    )


def fill_cart(user, *lines):
    """Put (product, quantity) pairs into the user's cart."""
    cart, _ = Cart.objects.get_or_create(user=user)
    for product, quantity in lines:
        CartItem.objects.create(cart=cart, product=product, quantity=quantity)
    return cart


class OrderTestCase(TestCase):
    """Shared starting situation: one customer and two products."""

    def setUp(self):
        self.category = Category.objects.create(name="Decor", slug="decor")
        self.user, self.address = make_customer()
        # MRP 1000 with 25% off: price 750
        self.lamp = make_product(self.category, "Test Lamp", "1000", 25, 10)
        # MRP 500 with no discount: price 500
        self.mug = make_product(self.category, "Test Mug", "500", 0, 10)


class PlaceOrderTests(OrderTestCase):
    def test_order_copies_the_details_and_adds_up_the_total(self):
        fill_cart(self.user, (self.lamp, 2), (self.mug, 1))

        order = place_order(self.user, self.address)

        self.assertEqual(order.total, Decimal("2000"))  # 2 x 750 + 500
        self.assertEqual(order.delivery_charge, Decimal("0"))
        self.assertEqual(order.status, Order.Status.PLACED)
        self.assertEqual(order.full_name, "Asha Sharma")
        self.assertEqual(order.mobile, "9876543210")
        self.assertEqual(order.city, "Bharatpur")
        self.assertEqual(order.items.count(), 2)

    def test_stock_is_reduced_and_every_change_is_logged(self):
        fill_cart(self.user, (self.lamp, 2), (self.mug, 1))

        place_order(self.user, self.address)

        self.lamp.refresh_from_db()
        self.mug.refresh_from_db()
        self.assertEqual(self.lamp.stock, 8)
        self.assertEqual(self.mug.stock, 9)
        self.assertEqual(
            StockLog.objects.filter(reason=StockLog.Reason.ONLINE_ORDER).count(), 2
        )

    def test_cart_is_emptied_after_ordering(self):
        cart = fill_cart(self.user, (self.lamp, 1))

        place_order(self.user, self.address)

        self.assertEqual(cart.items.count(), 0)

    def test_order_keeps_its_price_when_the_product_price_changes(self):
        fill_cart(self.user, (self.lamp, 1))
        order = place_order(self.user, self.address)

        self.lamp.mrp = Decimal("2000")
        self.lamp.save()

        self.assertEqual(self.lamp.price, Decimal("1500"))
        self.assertEqual(order.items.get().price, Decimal("750"))

    def test_empty_cart_is_refused(self):
        with self.assertRaises(CheckoutError):
            place_order(self.user, self.address)
        self.assertEqual(Order.objects.count(), 0)

    def test_hidden_product_is_refused(self):
        fill_cart(self.user, (self.lamp, 1))
        self.lamp.is_available = False
        self.lamp.save()

        with self.assertRaises(CheckoutError):
            place_order(self.user, self.address)
        self.assertEqual(Order.objects.count(), 0)

    def test_ordering_more_than_the_stock_is_refused(self):
        Product.objects.filter(pk=self.lamp.pk).update(stock=1)
        fill_cart(self.user, (self.lamp, 2))

        with self.assertRaises(CheckoutError):
            place_order(self.user, self.address)
        self.assertEqual(Order.objects.count(), 0)

    def test_one_sold_out_item_cancels_the_whole_order(self):
        cart = fill_cart(self.user, (self.lamp, 2), (self.mug, 1))
        Product.objects.filter(pk=self.mug.pk).update(stock=0)

        with self.assertRaises(CheckoutError):
            place_order(self.user, self.address)

        # Nothing was kept: no order, the lamp's stock is untouched, no log
        # rows, and the cart still holds everything.
        self.lamp.refresh_from_db()
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.lamp.stock, 10)
        self.assertEqual(StockLog.objects.count(), 0)
        self.assertEqual(cart.items.count(), 2)


class CancelOrderTests(OrderTestCase):
    def place(self):
        fill_cart(self.user, (self.lamp, 3))
        return place_order(self.user, self.address)

    def test_cancelling_restores_the_stock_and_logs_it(self):
        order = self.place()
        self.lamp.refresh_from_db()
        self.assertEqual(self.lamp.stock, 7)

        cancel_order(order)

        order.refresh_from_db()
        self.lamp.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertEqual(self.lamp.stock, 10)
        self.assertTrue(
            StockLog.objects.filter(reason=StockLog.Reason.ORDER_CANCELLED).exists()
        )

    def test_an_order_cannot_be_cancelled_twice(self):
        order = self.place()
        cancel_order(order)

        with self.assertRaises(CheckoutError):
            cancel_order(order)

        self.lamp.refresh_from_db()
        self.assertEqual(self.lamp.stock, 10)  # not 13

    def test_a_delivered_order_cannot_be_cancelled(self):
        order = self.place()
        mark_delivered(order)

        with self.assertRaises(CheckoutError):
            cancel_order(order)

        self.lamp.refresh_from_db()
        self.assertEqual(self.lamp.stock, 7)

    def test_an_order_cannot_be_delivered_twice(self):
        order = self.place()
        mark_delivered(order)

        with self.assertRaises(CheckoutError):
            mark_delivered(order)


class OrderViewTests(OrderTestCase):
    def setUp(self):
        super().setUp()
        fill_cart(self.user, (self.lamp, 1))
        self.order = place_order(self.user, self.address)
        self.other_user, _ = make_customer("ravi")

        self.detail_url = reverse("orders:order_detail", args=[self.order.pk])
        self.cancel_url = reverse("orders:cancel_order", args=[self.order.pk])

    def test_the_customer_can_see_their_own_order(self):
        self.client.force_login(self.user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)

    def test_another_customer_cannot_see_the_order(self):
        self.client.force_login(self.other_user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 404)

    def test_a_visitor_is_sent_to_the_login_page(self):
        url = reverse("orders:order_list")

        response = self.client.get(url)

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={url}",
            fetch_redirect_response=False,
        )

    def test_the_customer_can_cancel_their_own_order(self):
        self.client.force_login(self.user)

        response = self.client.post(self.cancel_url)

        self.assertRedirects(response, self.detail_url, fetch_redirect_response=False)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)

    def test_another_customer_cannot_cancel_the_order(self):
        self.client.force_login(self.other_user)

        response = self.client.post(self.cancel_url)

        self.assertEqual(response.status_code, 404)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PLACED)

    def test_cancelling_needs_a_post_request(self):
        self.client.force_login(self.user)

        response = self.client.get(self.cancel_url)

        self.assertEqual(response.status_code, 405)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PLACED)


class CheckoutPageTests(OrderTestCase):
    def setUp(self):
        super().setUp()
        self.checkout_url = reverse("orders:checkout")
        fill_cart(self.user, (self.lamp, 1))
        self.client.force_login(self.user)

    def unverify(self):
        Profile.objects.filter(user=self.user).update(is_mobile_verified=False)

    def test_an_unverified_customer_is_sent_to_verify_the_mobile(self):
        self.unverify()

        response = self.client.get(self.checkout_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:verify_mobile"), response.url)
        self.assertIn("next=%2Fcheckout%2F", response.url)

    def test_an_unverified_customer_cannot_order_by_posting_directly(self):
        self.unverify()

        self.client.post(self.checkout_url, {"address": self.address.pk})

        self.lamp.refresh_from_db()
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(self.lamp.stock, 10)

    def test_a_verified_customer_sees_the_checkout_page(self):
        response = self.client.get(self.checkout_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cash on Delivery")

    def test_a_verified_customer_can_place_an_order(self):
        response = self.client.post(self.checkout_url, {"address": self.address.pk})

        order = Order.objects.get()
        self.assertRedirects(
            response,
            reverse("orders:order_detail", args=[order.pk]),
            fetch_redirect_response=False,
        )
        self.lamp.refresh_from_db()
        self.assertEqual(self.lamp.stock, 9)

    @override_settings(REQUIRE_MOBILE_VERIFICATION=False)
    def test_the_verification_rule_can_be_switched_off(self):
        self.unverify()

        response = self.client.get(self.checkout_url)

        self.assertEqual(response.status_code, 200)

    def test_an_empty_cart_goes_back_to_the_cart_page(self):
        other_user, _ = make_customer("ravi")
        self.client.force_login(other_user)

        response = self.client.get(self.checkout_url)

        self.assertRedirects(
            response, reverse("orders:cart"), fetch_redirect_response=False
        )