from django.db import models
from authentication.models import Usermodels
from products.models import Category,Product,Variant,Variant_image
from checkout.models import OrderItem,Order


# Create your models here.
class Banner(models.Model):
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to='banners/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title