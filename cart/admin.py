from django.contrib import admin
from .models import Cart, CartItems

class CartItemsInline(admin.TabularInline):
    model = CartItems
    extra = 1  # Number of extra forms to display

class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'get_total_price')
    inlines = [CartItemsInline]

    def get_total_price(self, obj):
        return obj.get_total_price()
    get_total_price.short_description = 'Total Price'

class CartItemsAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'price', 'get_item_price')

    def get_item_price(self, obj):
        return obj.get_item_price()
    get_item_price.short_description = 'Item Price'

admin.site.register(Cart, CartAdmin)
admin.site.register(CartItems, CartItemsAdmin)
