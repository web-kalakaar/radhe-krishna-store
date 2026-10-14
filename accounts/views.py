from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AddressForm, ProfileForm, SignupForm
from .models import Profile


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