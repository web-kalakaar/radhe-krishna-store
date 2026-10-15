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