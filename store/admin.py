from django.contrib import admin

from .models import Category, Product, ProductFeature, ProductImage, StockLog


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3


class ProductFeatureInline(admin.TabularInline):
    model = ProductFeature
    extra = 3


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "brand",
        "mrp",
        "discount_percent",
        "price",
        "stock",
        "is_available",
    ]
    list_editable = ["is_available"]
    list_filter = ["category", "is_available", "is_featured"]
    search_fields = ["name", "brand"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [ProductImageInline, ProductFeatureInline]

    def get_readonly_fields(self, request, obj=None):
        # The stock of an existing product changes only through the stock page,
        # so that every change is recorded in the history.
        if obj:
            return ["price", "stock"]
        return ["price"]


@admin.register(StockLog)
class StockLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "product", "change", "stock_after", "reason", "note"]
    list_filter = ["reason"]
    search_fields = ["product__name", "note"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False