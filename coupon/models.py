from django.db import models
from django.utils import timezone



# Create your models here.
class Coupon(models.Model):
    coupon_code = models.CharField(max_length=50, unique=True)
    discount_price = models.IntegerField(default=150)
    minimum_amount = models.IntegerField(default=750)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    quantity = models.PositiveIntegerField()
    is_active = models.BooleanField(default=False)
    
    def __str__(self):
        return self.coupon_code
    
    def is_valid(self):
        now = timezone.now()
        return self.valid_from <= now <= self.valid_to and self.is_active
