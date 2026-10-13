from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from .models import Profile, mobile_validator

User = get_user_model()


class SignupForm(UserCreationForm):
    email = forms.EmailField()
    mobile = forms.CharField(
        max_length=10,
        validators=[mobile_validator],
        widget=forms.TextInput(attrs={"inputmode": "numeric"}),
    )

    field_order = ["username", "email", "mobile", "password1", "password2"]

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        """Create the user and the profile together, or neither."""
        user = super().save(commit=commit)
        Profile.objects.create(user=user, mobile=self.cleaned_data["mobile"])
        return user