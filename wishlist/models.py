from django.db import models
from authentication.models import Usermodels
from products.models import Product

# Create your models here.
class Wishlist(models.Model):
    user = models.ForeignKey(Usermodels, on_delete=models.CASCADE, related_name='wishlists')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wishlist for {self.user.name}"
    
class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.product.name} in {self.wishlist.user.name}'s wishlist"

    


        


