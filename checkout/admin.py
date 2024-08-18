from django.contrib import admin
from .models import Order, OrderItem, Wallet, WalletHistory

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    readonly_fields = ('subtotal',)
    fields = ('product', 'variant', 'price', 'quantity', 'subtotal')

    def subtotal(self, obj):
        return obj.subtotal()
    subtotal.short_description = 'Subtotal'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'address', 'total_price', 'payment_method', 'order_status', 'order_date', 'expected_delivery_date', 'delivered_date', 'coupon', 'shipping_charge')
    list_filter = ('order_status', 'order_date', 'expected_delivery_date', 'delivered_date', 'payment_method')
    search_fields = ('user__email', 'address__fullname', 'order_status')
    inlines = [OrderItemInline]

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'variant', 'price', 'quantity', 'subtotal')
    list_filter = ('order__order_date', 'order__delivered_date', 'order__expected_delivery_date')
    search_fields = ('order__user__email', 'product__name', 'variant__color')

class WalletHistoryInline(admin.TabularInline):
    model = WalletHistory
    extra = 1
    readonly_fields = ('updated_date', 'type', 'amount', 'new_balance')

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')
    search_fields = ('user__name', 'user__email')
    inlines = [WalletHistoryInline]

@admin.register(WalletHistory)
class WalletHistoryAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'updated_date', 'type', 'amount', 'new_balance')
    list_filter = ('type', 'updated_date')
    search_fields = ('wallet__user__name', 'wallet__user__email')
    readonly_fields = ('updated_date',)
