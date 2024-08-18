from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from .models import Category, Product, Variant,Variant_image,ProductOffer,Review, CategoryOffer

# Register your models here.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id','category_name', 'image')
    search_fields = ('category_name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'is_available', 'image')
    list_filter = ('is_available', 'category')
    search_fields = ('name', 'description', 'product_detail')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'color', 'price', 'stock')
    search_fields = ('product__name', 'color')
    prepopulated_fields = {'slug': ('color',)}

@admin.register(Variant_image)
class VariantImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'variant', 'variant_product', 'image')
    search_fields = ('variant__color', 'vairant__product__name')
    list_filter = ('variant__product',)

    def variant_product(self, obj):
        return obj.variant.product
    variant_product.short_description = 'Product'

@admin.register(ProductOffer)
class ProductOfferAdmin(admin.ModelAdmin):
    list_display = ('product', 'title', 'discount_percentage', 'start_date', 'end_date', 'is_active')
    list_filter = ('product', 'is_active')
    search_fields = ('title', 'product__name')
    date_hierarchy = 'start_date'    

@admin.register(CategoryOffer)
class CategoryOfferAdmin(admin.ModelAdmin):
    list_display = ('category', 'title', 'discount_percentage', 'start_date', 'end_date', 'is_active')    

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'rating', 'created_at') 
    list_filter = ('rating', 'created_at') 
    search_fields = ('user_username', 'product_name', 'comment') 
    ordering = ('-created_at',)