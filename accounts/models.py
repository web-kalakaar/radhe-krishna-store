 
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models, transaction

mobile_validator = RegexValidator(
    regex=r"^[6-9]\d{9}$",
    message="Enter a valid 10-digit Indian mobile number.",
)
pincode_validator = RegexValidator(
    regex=r"^\d{6}$",
    message="Enter a valid 6-digit pincode.",
)


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    mobile = models.CharField(max_length=10, validators=[mobile_validator])
    is_mobile_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Profile of {self.user}"


class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="addresses"
    )
    full_name = models.CharField(max_length=100)
    line1 = models.CharField("address line 1", max_length=200)
    line2 = models.CharField("address line 2", max_length=200, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=6, validators=[pincode_validator])
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "-id"]
        verbose_name_plural = "addresses"
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="one_default_address_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.full_name}, {self.city} - {self.pincode}"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not Address.objects.filter(user=self.user).exists():
                self.is_default = True  # the first address is always the default
            if self.is_default:
                Address.objects.filter(user=self.user, is_default=True).exclude(
                    pk=self.pk
                ).update(is_default=False)
            super().save(*args, **kwargs)