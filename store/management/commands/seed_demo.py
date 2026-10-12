import textwrap
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFont

from store.models import Category, Product, ProductFeature, ProductImage

PHOTOS_PER_PRODUCT = 4
BACKGROUNDS = ["#e8d5c4", "#c9d6df", "#d4e2d4", "#f1d4d4", "#e3dcf1", "#f7e7b4"]

# Product tuple: (name, brand, mrp, discount %, stock, featured, available)
CATALOG = {
    "photo-frames": {
        "name": "Photo Frames",
        "description": "A well-made frame to display your favourite memories.",
        "features": [("Material", "Wood"), ("Orientation", "Table top"), ("Glass", "Included")],
        "products": [
            ("Classic Wooden Photo Frame", "WoodCraft", 499, 20, 25, True, True),
            ("Collage Wall Frame Set of 5", "ArtNest", 1299, 35, 12, True, True),
            ("Mini Table Frame 4x6", "", 199, 0, 40, False, True),
            ("Golden Metal Photo Frame", "ArtNest", 799, 25, 0, False, True),
        ],
    },
    "sunglasses": {
        "name": "Sunglasses",
        "description": "Stylish sunglasses with UV protection.",
        "features": [("Frame Material", "Polycarbonate"), ("Lens", "UV protected"), ("Suitable For", "Men and Women")],
        "products": [
            ("Retro Round Sunglasses", "Visionary", 1499, 60, 18, True, True),
            ("Aviator Sunglasses", "Visionary", 1999, 71, 3, False, True),
            ("Square Black Sunglasses", "SunStyle", 999, 40, 30, False, True),
            ("Mirrored Sports Sunglasses", "SunStyle", 1299, 0, 10, False, False),
        ],
    },
    "cups-bottles": {
        "name": "Cups & Bottles",
        "description": "Everyday cups and bottles for home, office and travel.",
        "features": [("Material", "Stainless steel / ceramic"), ("Dishwasher Safe", "Yes"), ("Leak Proof", "Yes")],
        "products": [
            ("Ceramic Coffee Mug", "BrewBuddy", 349, 15, 50, True, True),
            ("Insulated Steel Water Bottle 750ml", "HydroMax", 899, 45, 22, True, True),
            ("Glass Tumbler Set of 4", "ClearHome", 599, 30, 2, False, True),
            ("Travel Coffee Cup with Lid", "BrewBuddy", 449, 0, 0, False, True),
        ],
    },
    "bags": {
        "name": "Bags",
        "description": "Durable and good-looking bags for daily use.",
        "features": [("Material", "Canvas"), ("Closure", "Zipper"), ("Water Resistant", "Yes")],
        "products": [
            ("Canvas Tote Bag", "UrbanCarry", 599, 40, 35, False, True),
            ("Casual Backpack 20L", "UrbanCarry", 1799, 55, 14, True, True),
            ("Mini Sling Bag", "", 699, 30, 20, False, True),
            ("Laptop Backpack 30L", "TrekPro", 2499, 50, 6, False, True),
        ],
    },
    "home-decor": {
        "name": "Home Decor",
        "description": "Aesthetic pieces to brighten up any room.",
        "features": [("Material", "Ceramic / fabric"), ("Style", "Modern aesthetic"), ("Placement", "Indoor")],
        "products": [
            ("Aesthetic Table Lamp", "Glowly", 1299, 35, 16, True, True),
            ("Ceramic Flower Vase", "HomeNest", 799, 20, 28, False, True),
            ("Wall Hanging Macrame", "KnotCraft", 899, 0, 9, False, True),
            ("Scented Candle Set of 3", "Glowly", 549, 25, 1, False, True),
        ],
    },
    "mens-clothing": {
        "name": "Men's Clothing",
        "description": "Comfortable everyday wear. Available sizes: S, M, L, XL.",
        "features": [("Fabric", "Cotton"), ("Fit", "Regular"), ("Care", "Machine wash")],
        "products": [
            ("Oversized Graphic T-Shirt", "StreetFit", 999, 50, 40, True, True),
            ("Slim Fit Cotton Shirt", "StreetFit", 1499, 40, 15, False, True),
            ("Relaxed Fit Cargo Pants", "UrbanWear", 1999, 45, 8, False, True),
            ("Hooded Sweatshirt", "UrbanWear", 1799, 30, 0, False, True),
        ],
    },
}


def make_photo(label, background):
    """Return a square placeholder JPEG with the product name written on it."""
    image = Image.new("RGB", (800, 800), background)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=48)
    draw.multiline_text(
        (400, 400),
        textwrap.fill(label, 16),
        fill="#333333",
        font=font,
        anchor="mm",
        align="center",
    )
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


class Command(BaseCommand):
    help = "Create demo categories and products with generated placeholder photos."

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0

        for slug, data in CATALOG.items():
            category, _ = Category.objects.get_or_create(
                slug=slug, defaults={"name": data["name"]}
            )

            for name, brand, mrp, discount, stock, featured, available in data["products"]:
                product_slug = slugify(name)
                if Product.objects.filter(slug=product_slug).exists():
                    continue

                product = Product.objects.create(
                    category=category,
                    name=name,
                    slug=product_slug,
                    brand=brand,
                    description=f"{name}. {data['description']}",
                    mrp=mrp,
                    discount_percent=discount,
                    stock=stock,
                    is_featured=featured,
                    is_available=available,
                )

                for order, (feature_name, value) in enumerate(data["features"]):
                    ProductFeature.objects.create(
                        product=product, name=feature_name, value=value, sort_order=order
                    )

                for number in range(1, PHOTOS_PER_PRODUCT + 1):
                    background = BACKGROUNDS[(product.pk + number) % len(BACKGROUNDS)]
                    photo = make_photo(f"{name}\n(photo {number})", background)
                    ProductImage.objects.create(
                        product=product,
                        sort_order=number,
                        image=ContentFile(photo, name=f"{product_slug}-{number}.jpg"),
                    )

                created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} demo products."))