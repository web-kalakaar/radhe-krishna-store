from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import OTP, Address, Profile
from .otp import MAX_ATTEMPTS, OTPError, deliver, generate_code, issue_otp, verify_otp

User = get_user_model()
MOBILE = "9876543210"


def make_user(username="asha", verified=False, **extra):
    user = User.objects.create_user(
        username=username, password="test-pass-123", **extra
    )
    Profile.objects.create(user=user, mobile=MOBILE, is_mobile_verified=verified)
    return user


def make_address(user, **overrides):
    values = {
        "full_name": "Asha Sharma",
        "line1": "12 Main Road",
        "city": "Bharatpur",
        "state": "Rajasthan",
        "pincode": "321001",
    }
    values.update(overrides)
    return Address.objects.create(user=user, **values)


class OTPTestCase(TestCase):
    """Shared helpers for tests that need a customer and a known code."""

    def setUp(self):
        self.user = make_user()
        self.request = RequestFactory().get("/")

    def issue(self, code="123456"):
        # Fix the code so the test knows it, and keep it out of the terminal.
        with patch("accounts.otp.generate_code", return_value=code), patch(
            "accounts.otp.deliver"
        ):
            issue_otp(self.request, self.user, MOBILE)

    def age_codes(self, seconds=120):
        """Pretend the codes were created `seconds` ago (to get past the resend wait)."""
        OTP.objects.update(created_at=timezone.now() - timedelta(seconds=seconds))

    def is_verified(self):
        return Profile.objects.get(user=self.user).is_mobile_verified


class GenerateCodeTests(TestCase):
    def test_codes_are_six_digits_with_leading_zeros_kept(self):
        for _ in range(300):
            code = generate_code()
            self.assertEqual(len(code), 6)
            self.assertTrue(code.isdigit())


class DeliverTests(TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")

    @override_settings(OTP_BACKEND="console")
    def test_console_backend_prints_the_code(self):
        with patch("builtins.print") as fake_print:
            deliver(self.request, MOBILE, "123456")
        self.assertIn("123456", fake_print.call_args[0][0])

    @override_settings(OTP_BACKEND="demo")
    def test_demo_backend_prints_the_code_even_without_a_message_store(self):
        with patch("builtins.print") as fake_print:
            deliver(self.request, MOBILE, "123456")
        fake_print.assert_called_once()

    @override_settings(OTP_BACKEND="sms")
    def test_an_unknown_backend_fails_loudly(self):
        with self.assertRaises(ImproperlyConfigured):
            deliver(self.request, MOBILE, "123456")


class OTPRuleTests(OTPTestCase):
    def test_the_correct_code_verifies_the_mobile(self):
        self.issue()

        verify_otp(self.user, MOBILE, "123456")

        self.assertTrue(self.is_verified())

    def test_only_a_hash_of_the_code_is_stored(self):
        self.issue()

        self.assertNotEqual(OTP.objects.get().code_hash, "123456")

    def test_a_wrong_code_is_refused_and_counted(self):
        self.issue()

        with self.assertRaisesMessage(OTPError, f"{MAX_ATTEMPTS - 1} attempts left"):
            verify_otp(self.user, MOBILE, "000000")

        self.assertEqual(OTP.objects.get().attempts, 1)
        self.assertFalse(self.is_verified())

    def test_the_code_dies_after_too_many_wrong_attempts(self):
        self.issue()

        for _ in range(MAX_ATTEMPTS):
            with self.assertRaises(OTPError):
                verify_otp(self.user, MOBILE, "000000")

        # Even the correct code no longer works.
        with self.assertRaises(OTPError):
            verify_otp(self.user, MOBILE, "123456")
        self.assertFalse(self.is_verified())

    def test_an_expired_code_is_refused(self):
        self.issue()
        OTP.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

        with self.assertRaisesMessage(OTPError, "expired"):
            verify_otp(self.user, MOBILE, "123456")

        self.assertFalse(self.is_verified())

    def test_a_code_can_be_used_only_once(self):
        self.issue()
        verify_otp(self.user, MOBILE, "123456")
        Profile.objects.filter(user=self.user).update(is_mobile_verified=False)

        with self.assertRaises(OTPError):
            verify_otp(self.user, MOBILE, "123456")

        self.assertFalse(self.is_verified())

    def test_a_new_code_cancels_the_old_one(self):
        self.issue("111111")
        self.age_codes()
        self.issue("222222")

        with self.assertRaises(OTPError):
            verify_otp(self.user, MOBILE, "111111")
        self.assertFalse(self.is_verified())

        verify_otp(self.user, MOBILE, "222222")
        self.assertTrue(self.is_verified())

    def test_a_new_code_cannot_be_requested_straight_away(self):
        self.issue()

        with self.assertRaisesMessage(OTPError, "Please wait"):
            self.issue()

        self.assertEqual(OTP.objects.count(), 1)

    def test_a_new_code_can_be_requested_after_the_wait(self):
        self.issue()
        self.age_codes()

        self.issue()

        self.assertEqual(OTP.objects.count(), 2)

    def test_a_code_does_not_verify_a_number_changed_after_it_was_sent(self):
        self.issue()
        Profile.objects.filter(user=self.user).update(mobile="9123456789")

        with self.assertRaises(OTPError):
            verify_otp(self.user, MOBILE, "123456")

        self.assertFalse(self.is_verified())


class VerifyMobileViewTests(OTPTestCase):
    def setUp(self):
        super().setUp()
        self.verify_url = reverse("accounts:verify_mobile")
        self.send_url = reverse("accounts:otp_send")
        self.client.force_login(self.user)

    def test_a_visitor_is_sent_to_the_login_page(self):
        self.client.logout()

        response = self.client.get(self.verify_url)

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={self.verify_url}",
            fetch_redirect_response=False,
        )

    def test_asking_for_a_code_creates_an_otp(self):
        with patch("accounts.otp.deliver"):
            response = self.client.post(self.send_url)

        self.assertRedirects(response, self.verify_url, fetch_redirect_response=False)
        self.assertEqual(OTP.objects.filter(user=self.user).count(), 1)

    def test_a_code_cannot_be_requested_with_get(self):
        response = self.client.get(self.send_url)

        self.assertEqual(response.status_code, 405)

    def test_the_correct_code_verifies_and_returns_to_the_next_page(self):
        self.issue()

        response = self.client.post(
            self.verify_url, {"code": "123456", "next": "/checkout/"}
        )

        self.assertRedirects(response, "/checkout/", fetch_redirect_response=False)
        self.assertTrue(self.is_verified())

    def test_a_wrong_code_returns_to_the_page_and_stays_unverified(self):
        self.issue()

        response = self.client.post(self.verify_url, {"code": "000000"})

        self.assertRedirects(response, self.verify_url, fetch_redirect_response=False)
        self.assertFalse(self.is_verified())

    def test_a_next_address_on_another_website_is_ignored(self):
        self.issue()

        response = self.client.post(
            self.verify_url, {"code": "123456", "next": "https://example.com/"}
        )

        self.assertRedirects(
            response, reverse("accounts:profile"), fetch_redirect_response=False
        )

    def test_a_verified_customer_is_passed_straight_through(self):
        Profile.objects.filter(user=self.user).update(is_mobile_verified=True)

        response = self.client.get(self.verify_url + "?next=/checkout/")

        self.assertRedirects(response, "/checkout/", fetch_redirect_response=False)

    def test_another_customer_cannot_use_the_code(self):
        self.issue()
        other = make_user("ravi")
        self.client.force_login(other)

        self.client.post(self.verify_url, {"code": "123456"})

        self.assertFalse(Profile.objects.get(user=other).is_mobile_verified)


class ProfileTests(TestCase):
    def test_changing_the_mobile_resets_verification(self):
        user = make_user(verified=True)
        self.client.force_login(user)

        self.client.post(reverse("accounts:profile"), {"mobile": "9123456789"})

        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.mobile, "9123456789")
        self.assertFalse(profile.is_mobile_verified)

    def test_saving_the_same_mobile_keeps_verification(self):
        user = make_user(verified=True)
        self.client.force_login(user)

        self.client.post(reverse("accounts:profile"), {"mobile": MOBILE})

        self.assertTrue(Profile.objects.get(user=user).is_mobile_verified)


class SignupTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:signup")

    def data(self, **overrides):
        values = {
            "username": "newbie",
            "email": "new@example.com",
            "mobile": MOBILE,
            "password1": "Str0ng-pass-987",
            "password2": "Str0ng-pass-987",
        }
        values.update(overrides)
        return values

    def test_signup_creates_the_user_and_profile_and_logs_in(self):
        response = self.client.post(self.url, self.data())

        self.assertRedirects(
            response, reverse("store:home"), fetch_redirect_response=False
        )
        user = User.objects.get(username="newbie")
        self.assertEqual(user.profile.mobile, MOBILE)
        self.assertFalse(user.profile.is_mobile_verified)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_an_email_that_is_already_used_is_refused_in_any_letter_case(self):
        User.objects.create_user("old", email="New@Example.com", password="x-pass-123")

        response = self.client.post(self.url, self.data())

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "email",
            "An account with this email already exists.",
        )
        self.assertFalse(User.objects.filter(username="newbie").exists())

    def test_an_invalid_mobile_creates_no_account(self):
        response = self.client.post(self.url, self.data(mobile="12345"))

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "mobile",
            "Enter a valid 10-digit Indian mobile number.",
        )
        self.assertFalse(User.objects.filter(username="newbie").exists())


class AddressModelTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_the_first_address_becomes_the_default(self):
        self.assertTrue(make_address(self.user).is_default)

    def test_a_later_address_is_not_the_default_unless_asked(self):
        make_address(self.user)

        self.assertFalse(make_address(self.user).is_default)

    def test_a_new_default_replaces_the_old_default(self):
        first = make_address(self.user)

        second = make_address(self.user, is_default=True)

        first.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)

    def test_each_customer_has_their_own_default(self):
        make_address(self.user)
        make_address(make_user("ravi"))

        self.assertEqual(Address.objects.filter(is_default=True).count(), 2)


class AddressViewTests(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.stranger = make_user("ravi")

    def test_another_customer_cannot_edit_the_address(self):
        address = make_address(self.owner)
        self.client.force_login(self.stranger)

        response = self.client.get(reverse("accounts:address_edit", args=[address.pk]))

        self.assertEqual(response.status_code, 404)

    def test_another_customer_cannot_delete_the_address(self):
        address = make_address(self.owner)
        self.client.force_login(self.stranger)

        response = self.client.post(
            reverse("accounts:address_delete", args=[address.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Address.objects.filter(pk=address.pk).exists())

    def test_deleting_the_default_makes_the_newest_remaining_address_the_default(self):
        default = make_address(self.owner)
        remaining = make_address(self.owner)
        self.client.force_login(self.owner)

        self.client.post(reverse("accounts:address_delete", args=[default.pk]))

        remaining.refresh_from_db()
        self.assertTrue(remaining.is_default)