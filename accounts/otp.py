import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import OTP, Profile

OTP_VALID_MINUTES = 5
RESEND_AFTER_SECONDS = 60
MAX_ATTEMPTS = 5


class OTPError(Exception):
    """The OTP step failed. The message is shown to the customer."""


def generate_code():
    """A random 6-digit code. `secrets` is meant for security; `random` is not."""
    return f"{secrets.randbelow(10**6):06d}"


def deliver(request, mobile, code):
    """Hand the code to the customer. Only this function knows how."""
    backend = settings.OTP_BACKEND
    if backend in {"demo", "console"}:
        print(f"[DEMO OTP] {mobile}: {code}")
        if backend == "demo":
            messages.info(
                request,
                f"Demo mode: your OTP is {code}. No SMS is sent.",
                fail_silently=True,
            )
    else:
        raise ImproperlyConfigured(
            f"OTP_BACKEND '{backend}' is not available. Use 'demo' or 'console'."
        )


@transaction.atomic
def issue_otp(request, user, mobile):
    """Create a new code for this user and number, and deliver it."""
    now = timezone.now()

    last = OTP.objects.filter(user=user).first()
    if last:
        waited = (now - last.created_at).total_seconds()
        if waited < RESEND_AFTER_SECONDS:
            wait = int(RESEND_AFTER_SECONDS - waited) + 1
            raise OTPError(f"Please wait {wait} seconds before asking for a new code.")

    # Older codes stop working as soon as a new one is sent.
    OTP.objects.filter(user=user, is_used=False).update(is_used=True)

    code = generate_code()
    OTP.objects.create(
        user=user,
        mobile=mobile,
        code_hash=make_password(code),
        expires_at=now + timedelta(minutes=OTP_VALID_MINUTES),
    )
    deliver(request, mobile, code)


def verify_otp(user, mobile, code):
    """Check the code. On success the profile is marked as verified."""
    # Not wrapped in transaction.atomic on purpose: raising an error inside
    # atomic() undoes the changes made inside it, including the attempt counter.
    otp = OTP.objects.filter(user=user, mobile=mobile, is_used=False).first()

    if otp is None:
        raise OTPError("There is no active code. Please request a new one.")

    if otp.expires_at <= timezone.now():
        OTP.objects.filter(pk=otp.pk).update(is_used=True)
        raise OTPError("This code has expired. Please request a new one.")

    if not check_password(code, otp.code_hash):
        OTP.objects.filter(pk=otp.pk).update(attempts=F("attempts") + 1)
        otp.refresh_from_db()
        if otp.attempts >= MAX_ATTEMPTS:
            OTP.objects.filter(pk=otp.pk).update(is_used=True)
            raise OTPError("Too many wrong attempts. Please request a new code.")
        raise OTPError(f"Wrong code. {MAX_ATTEMPTS - otp.attempts} attempts left.")

    # Correct code: use it up in one step, so it can never be used twice.
    if not OTP.objects.filter(pk=otp.pk, is_used=False).update(is_used=True):
        raise OTPError("This code has already been used. Please request a new one.")

    verified = Profile.objects.filter(user=user, mobile=mobile).update(
        is_mobile_verified=True
    )
    if not verified:
        raise OTPError("Your mobile number changed. Please request a new code.")