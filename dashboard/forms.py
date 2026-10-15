from django import forms

from orders.models import Order
from store.models import Product
 


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