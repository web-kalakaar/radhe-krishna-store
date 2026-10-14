from django.contrib import admin

from .models import Address, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "mobile", "is_mobile_verified"]
    search_fields = ["user__username", "mobile"]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["user", "full_name", "city", "pincode", "is_default"]
    search_fields = ["user__username", "full_name", "pincode"]