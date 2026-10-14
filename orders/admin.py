from django.contrib import admin

from .models import Cart, CartItem, Order, OrderItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["user", "item_count", "total", "updated_at"]
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ["product", "product_name", "price", "quantity"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "user", "total", "status", "created_at"]
    list_filter = ["status", "payment_method"]
    search_fields = ["user__username", "full_name", "mobile"]
    readonly_fields = ["total", "delivery_charge", "created_at"]
    inlines = [OrderItemInline]