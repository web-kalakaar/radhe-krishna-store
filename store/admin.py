from django.contrib import admin

from .models import Category, Product, ProductFeature, ProductImage


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
    list_editable = ["stock", "is_available"]
    list_filter = ["category", "is_available", "is_featured"]
    search_fields = ["name", "brand"]
    prepopulated_fields = {"slug": ["name"]}
    readonly_fields = ["price"]
    inlines = [ProductImageInline, ProductFeatureInline]