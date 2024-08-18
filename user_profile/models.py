from django.db import models
from authentication.models import Usermodels
from django.core.validators import MinLengthValidator
from django.utils.translation import gettext_lazy as _

class UserAddress(models.Model):
    user = models.ForeignKey(Usermodels, on_delete=models.CASCADE)
    fullname = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    apartment = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    type = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.fullname}, {self.street}, {self.city},{self.district}, {self.state}"