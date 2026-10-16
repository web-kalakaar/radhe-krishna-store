from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import AddressForm, OTPForm, ProfileForm, SignupForm
from .models import Profile
from .otp import OTPError, issue_otp, verify_otp

def signup(request):
    if request.user.is_authenticated:
        return redirect("store:home")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Your account has been created.")
            return redirect("store:home")
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})


@login_required
def profile(request):
    # Users made with createsuperuser have no profile yet, so this may be None.
    profile = Profile.objects.filter(user=request.user).first()

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=profile)

    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "profile": profile,
            "addresses": request.user.addresses.all(),
        },
    )
    
@login_required
def address_add(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, "Address saved.")
            return redirect("accounts:profile")
    else:
        form = AddressForm()

    return render(
        request, "accounts/address_form.html", {"form": form, "title": "Add address"}
    )


@login_required
def address_edit(request, pk):
    address = get_object_or_404(request.user.addresses, pk=pk)

    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "Address updated.")
            return redirect("accounts:profile")
    else:
        form = AddressForm(instance=address)

    return render(
        request, "accounts/address_form.html", {"form": form, "title": "Edit address"}
    )


@login_required
def address_delete(request, pk):
    address = get_object_or_404(request.user.addresses, pk=pk)

    if request.method == "POST":
        was_default = address.is_default
        address.delete()
        if was_default:
            # Keep one default: promote the newest remaining address.
            newest = request.user.addresses.first()
            if newest:
                newest.is_default = True
                newest.save()
        messages.success(request, "Address deleted.")
        return redirect("accounts:profile")

    return render(request, "accounts/address_confirm_delete.html", {"address": address})


def _safe_next(request):
    """The page to return to after verifying, or "" if it is missing or unsafe."""
    next_url = request.POST.get("next") or request.GET.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return ""


def _verify_redirect(next_url):
    url = reverse("accounts:verify_mobile")
    if next_url:
        url += "?" + urlencode({"next": next_url})
    return redirect(url)


@login_required
def verify_mobile(request):
    profile = Profile.objects.filter(user=request.user).first()
    if profile is None:
        messages.warning(request, "Please add your mobile number first.")
        return redirect("accounts:profile")

    next_url = _safe_next(request)

    if profile.is_mobile_verified and next_url:
        return redirect(next_url)

    if request.method == "POST" and not profile.is_mobile_verified:
        form = OTPForm(request.POST)
        if form.is_valid():
            try:
                verify_otp(request.user, profile.mobile, form.cleaned_data["code"])
            except OTPError as error:
                messages.error(request, str(error))
                return _verify_redirect(next_url)
            messages.success(request, "Your mobile number is verified.")
            return redirect(next_url or "accounts:profile")
    else:
        form = OTPForm()

    return render(
        request,
        "accounts/verify_mobile.html",
        {
            "form": form,
            "profile": profile,
            "masked_mobile": "******" + profile.mobile[-4:],
            "next_url": next_url,
        },
    )


@login_required
@require_POST
def otp_send(request):
    profile = Profile.objects.filter(user=request.user).first()
    if profile is None:
        messages.warning(request, "Please add your mobile number first.")
        return redirect("accounts:profile")

    next_url = _safe_next(request)

    if profile.is_mobile_verified:
        messages.info(request, "Your mobile number is already verified.")
        return redirect(next_url or "accounts:profile")

    try:
        issue_otp(request, request.user, profile.mobile)
    except OTPError as error:
        messages.error(request, str(error))
    else:
        messages.success(
            request,
            f"A 6-digit code has been sent to ******{profile.mobile[-4:]}. "
            "It is valid for 5 minutes.",
        )

    return _verify_redirect(next_url)