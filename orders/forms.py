from django import forms
from accounts.models import Address

class QuantityForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=99)
    
class AddressChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, address):
        parts = [address.full_name, address.line1, address.line2, address.city]
        text = ", ".join(part for part in parts if part)
        return f"{text} - {address.pincode}"


class CheckoutForm(forms.Form):
    address = AddressChoiceField(
        queryset=Address.objects.none(),
        widget=forms.RadioSelect,
        empty_label=None,
        error_messages={"required": "Please choose a delivery address."},
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        addresses = user.addresses.all()
        self.fields["address"].queryset = addresses
        default = addresses.filter(is_default=True).first()
        if default:
            self.fields["address"].initial = default.pk