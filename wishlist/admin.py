from django.contrib import admin
from .models import Wishlist, WishlistItem

class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 1

class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__name', 'user__email')
    inlines = [WishlistItemInline]

class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('wishlist', 'product')
    search_fields = ('wishlist__user__name', 'wishlist__user__email', 'product__name')

admin.site.register(Wishlist, WishlistAdmin)
admin.site.register(WishlistItem, WishlistItemAdmin)
