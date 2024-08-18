from django.utils.text import slugify
from django.urls import reverse
from django.utils import timezone
from django.db import models
from django.db.models import Count
from decimal import Decimal
from authentication.models import Usermodels


class Category(models.Model):
    # Automatically generated primary key field (id)
    category_name = models.CharField(max_length=100, default='Uncategorized')
    image = models.ImageField(upload_to='static/media/category_images/', blank=True,null=True)
    is_listed = models.BooleanField(default=True)
    slug = models.SlugField(unique=True,blank=True,null=True)

    def save(self, *args, **kwargs):
        was_listed = False
        if self.pk:
            previous = Category.objects.get(pk=self.pk)
            was_listed = previous.is_listed

        self.slug = slugify(self.category_name)
        super(Category,self).save(*args, **kwargs)

        if self.is_listed != was_listed:
            Product.objects.filter(category=self).update(is_available=self.is_listed)
            for product in Product.objects.filter(category=self):
                product.variants.update(is_available=self.is_listed)

    def __str__(self):
        return self.category_name
    
    


class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey('Category',on_delete=models.CASCADE, default=1)
    image = models.ImageField(upload_to='product_images/', blank=True,null=True)
    description =  models.TextField(default='', blank=True, null=True)
    product_detail = models.TextField(default='', blank=True, null=True)
    is_available = models.BooleanField(default=True)  # This field indicates if the product is available or soft-deleted
    slug = models.SlugField(unique=True,blank=True,null=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Product,self).save(*args, **kwargs)


    def __str__(self):
        return self.name
    
    def get_discounted_price(self):
        # Get active product offers
        product_offers = ProductOffer.objects.filter(product=self, is_active=True)
        product_discount = Decimal('0')

        if product_offers.exists():
            offer = product_offers.first()
            if offer.is_valid():
                product_discount = (offer.discount_percentage / Decimal('100'))

        # Get active category offers
        category = self.category
        category_offers = CategoryOffer.objects.filter(category=category, is_active=True)
        category_discount = Decimal('0')

        if category_offers.exists():
            offer = category_offers.first()
            if offer.is_valid():
                category_discount = (offer.discount_percentage / Decimal('100'))

        # Determine the higher discount
        discount_percentage = max(product_discount, category_discount)

        if discount_percentage > Decimal('0'):
            variant = self.variants.first()
            if variant:
                original_price = variant.price  # This is a Decimal
                discount = discount_percentage * original_price
                return original_price - discount

        return None

    
class Variant(models.Model):
    product = models.ForeignKey(Product, related_name='variants', on_delete=models.CASCADE)  
    color = models.CharField(max_length=50) 
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    is_available = models.BooleanField(default=True) 
    slug = models.SlugField(unique=False,blank=True,null=True)
    max_quantity_per_person = models.PositiveIntegerField(default=10)
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.color)
        super(Variant,self).save(*args, **kwargs)

    def __str__(self):
        return self.color
    

class Variant_image(models.Model):
    variant = models.ForeignKey(Variant,related_name='images', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    image = models.ImageField( upload_to="variant_images/", blank=True,null=True)  
     
    def __str__(self):
        return f"Image for {self.variant.product.name} - {self.variant.color}"     

class CategoryOffer(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    discount_percentage = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.title} - {self.category.category_name}'

    def is_valid(self):
        today = timezone.now().date()
        return self.is_active and self.start_date <= today <= self.end_date

    def get_discounted_price(self, product):
        if self.is_valid():
            offers = ProductOffer.objects.filter(product=product, is_active=True)
            if not offers.exists():
                original_price = product.variants.first().price
                discount = (self.discount_percentage / Decimal('100')) * original_price
                return original_price - discount
        return None

class ProductOffer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    discount_percentage = models.PositiveIntegerField()  
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)  

    def __str__(self):
        return f'{self.title} - {self.product.name}'

    def is_valid(self):
        today = timezone.now().date()
        return self.is_active and self.start_date <= today <= self.end_date
    
class Review(models.Model):
    user = models.ForeignKey(Usermodels, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    rating = models.FloatField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.name} - {self.product.name} - {self.rating}'    