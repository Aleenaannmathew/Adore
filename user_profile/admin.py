from django.contrib import admin
from .models import UserAddress

class UserAddressAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'fullname', 'country', 'city', 'district', 'state', 'zip_code', 'phone', 'is_active')
    list_filter = ['country', 'city','district',  'state', 'is_active']
    search_fields = ['fullname', 'street', 'city', 'district', 'state', 'zip_code', 'phone']

admin.site.register(UserAddress, UserAddressAdmin)
