from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

mobile_validator = RegexValidator(
    regex=r"^[6-9]\d{9}$",
    message="Enter a valid 10-digit Indian mobile number.",
)


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    mobile = models.CharField(max_length=10, validators=[mobile_validator])
    is_mobile_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Profile of {self.user}"