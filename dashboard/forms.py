from django import forms

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