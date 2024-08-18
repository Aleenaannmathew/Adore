from django.db import models
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from authentication.models import Usermodels
from products.models import Product
from products.models import Variant

# Create your models here.

class Cart(models.Model):
    user = models.ForeignKey(Usermodels, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart for {self.user.name}"

    def get_total_price(self):
        total_price = sum(item.get_item_price() for item in self.items.all())
        return total_price if total_price else 0.00

    
class CartItems(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Variant, on_delete=models.CASCADE)
    quantity = models.PositiveBigIntegerField(default=0)
    price = models.DecimalField( max_digits=8, decimal_places=2, default=0.00) 

    
    def get_item_price(self):
        return self.price * self.quantity

    def save(self, *args, **kwargs):
        product = self.product
        product_discounted_price = product.product.get_discounted_price()
        self.price = product_discounted_price if product_discounted_price else product.price
        super().save(*args, **kwargs)
    

    



