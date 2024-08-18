from django.db import models
from django.utils import timezone
from authentication.models import Usermodels
from products.models import Product, Variant
from user_profile.models import UserAddress
from coupon.models import Coupon
from datetime import timedelta

class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('ordered', 'Ordered'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('pending', 'Pending'),
    ]
    
    user = models.ForeignKey(Usermodels, on_delete=models.CASCADE)
    address = models.ForeignKey(UserAddress, on_delete=models.CASCADE)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20)
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    order_date = models.DateTimeField(default=timezone.now)
    expected_delivery_date = models.DateTimeField(blank=True, null=True)
    delivered_date = models.DateTimeField(blank=True, null=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    shipping_charge = models.FloatField(default=0.0)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if not self.expected_delivery_date:
            self.expected_delivery_date = self.order_date + timedelta(days=7)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} by {self.user.email}"

class OrderItem(models.Model):
    RETURN_STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        
    ]
    
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2) 
    quantity = models.PositiveIntegerField()
    productReturn = models.BooleanField(default=False)
    return_status = models.CharField(max_length=20, choices=RETURN_STATUS_CHOICES, default='')

    def __str__(self):
        return f"{self.quantity} x {self.product.name} ({self.variant.color})"
    
    def subtotal(self):
        if self.price is not None and self.quantity is not None:
            return self.price * self.quantity
        return 0


class Wallet(models.Model):
    user = models.ForeignKey(Usermodels, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.user.name} - Wallet'
    
class WalletHistory(models.Model):
    CREDIT = 'credit'
    DEBIT = 'debit'
    TRANSACTION_TYPES = [
        (CREDIT, 'Credit'),
        (DEBIT, 'Debit')
    ]   

    wallet = models.ForeignKey(Wallet, related_name='history', on_delete=models.CASCADE)
    updated_date = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=8, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    new_balance = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.wallet.user.name} - {self.type} - {self.amount}' 





