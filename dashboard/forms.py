from django import forms
from django.forms import inlineformset_factory
from store.models import Product, ProductFeature, ProductImage
from orders.models import Order


class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["delivery_boy_name", "delivery_boy_mobile"]
        labels = {
            "delivery_boy_name": "Delivery person's name",
            "delivery_boy_mobile": "Delivery person's mobile",
        }
        widgets = {
            "delivery_boy_mobile": forms.TextInput(attrs={"inputmode": "numeric"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("delivery_boy_mobile") and not cleaned_data.get(
            "delivery_boy_name"
        ):
            self.add_error("delivery_boy_name", "Enter the delivery person's name too.")
        return cleaned_data
class StockAdjustForm(forms.Form):
    ACTION_CHOICES = [
        ("sold", "Sold offline (subtract)"),
        ("restock", "Restocked (add)"),
        ("set", "Set exact count"),
    ]

    action = forms.ChoiceField(choices=ACTION_CHOICES)
    quantity = forms.IntegerField(min_value=0, max_value=100000)
    note = forms.CharField(max_length=200, required=False)

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get("action") in {"sold", "restock"}
            and cleaned_data.get("quantity") == 0
        ):
            self.add_error("quantity", "Enter a quantity of at least 1.")
        return cleaned_data
    
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "category",
            "name",
            "brand",
            "description",
            "mrp",
            "discount_percent",
            "stock",
            "is_available",
            "is_featured",
        ]
        labels = {
            "is_available": "Available in the shop",
            "is_featured": "Show on the home page (featured)",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # After creation, stock changes only through the stock page,
            # so that every change is recorded in the history.
            del self.fields["stock"]

    def clean_mrp(self):
        mrp = self.cleaned_data["mrp"]
        if mrp <= 0:
            raise forms.ValidationError("MRP must be more than 0.")
        return mrp
    
    
MAX_IMAGE_MB = 5


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "sort_order"]
        labels = {"sort_order": "Display order"}
        widgets = {"image": forms.FileInput(attrs={"accept": "image/*"})}

    def clean_image(self):
        image = self.cleaned_data.get("image")
        # Check the size only for a file uploaded just now, not for saved photos.
        if image and "image" in self.changed_data and image.size > MAX_IMAGE_MB * 1024 * 1024:
            raise forms.ValidationError(
                f"This photo is too large. The maximum size is {MAX_IMAGE_MB} MB."
            )
        return image


ProductImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    form=ProductImageForm,
    extra=3,
    can_delete=True,
)


class ProductFeatureForm(forms.ModelForm):
    class Meta:
        model = ProductFeature
        fields = ["name", "value", "sort_order"]
        labels = {"name": "Feature", "sort_order": "Order"}
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Material"}),
            "value": forms.TextInput(attrs={"placeholder": "e.g. Wood"}),
        }


ProductFeatureFormSet = inlineformset_factory(
    Product,
    ProductFeature,
    form=ProductFeatureForm,
    extra=4,
    can_delete=True,
)