from django import forms

SORT_CHOICES = [
    ("", "Newest first"),
    ("price_asc", "Price: low to high"),
    ("price_desc", "Price: high to low"),
    ("discount", "Biggest discount"),
]

SORT_FIELDS = {
    "price_asc": "price",
    "price_desc": "-price",
    "discount": "-discount_percent",
}


class ProductFilterForm(forms.Form):
    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        label="Min price",
        widget=forms.NumberInput(attrs={"placeholder": "Min ₹"}),
    )
    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        label="Max price",
        widget=forms.NumberInput(attrs={"placeholder": "Max ₹"}),
    )
    in_stock = forms.BooleanField(required=False, label="In stock only")
    sort = forms.ChoiceField(choices=SORT_CHOICES, required=False, label="Sort by")

    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get("min_price")
        max_price = cleaned_data.get("max_price")
        if min_price is not None and max_price is not None and min_price > max_price:
            self.add_error("max_price", "Max price must be higher than min price.")
        return cleaned_data

    def filter_queryset(self, queryset):
        """Apply the chosen filters and sorting. Invalid input is ignored."""
        if not self.is_valid():
            return queryset

        data = self.cleaned_data
        if data["min_price"] is not None:
            queryset = queryset.filter(price__gte=data["min_price"])
        if data["max_price"] is not None:
            queryset = queryset.filter(price__lte=data["max_price"])
        if data["in_stock"]:
            queryset = queryset.filter(stock__gt=0)

        ordering = SORT_FIELDS.get(data["sort"])
        if ordering:
            queryset = queryset.order_by(ordering, "id")
        return queryset