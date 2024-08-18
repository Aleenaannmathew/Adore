from django.contrib import admin
from .models import Coupon

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('coupon_code', 'discount_price', 'minimum_amount', 'valid_from', 'valid_to', 'quantity', 'is_active')
    list_filter = ('is_active', 'valid_from', 'valid_to')
    search_fields = ('coupon_code',)
    actions = ['activate_coupons', 'deactivate_coupons']

    def activate_coupons(self, request, queryset):
        queryset.update(is_active=True)
    activate_coupons.short_description = 'Activate selected coupons'

    def deactivate_coupons(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_coupons.short_description = 'Deactivate selected coupons'