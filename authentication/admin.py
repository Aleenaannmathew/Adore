from django.contrib import admin

from .models import Usermodels,Referral
# Register your models here.

class UsermodelsAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'is_verified', 'is_block', 'join_date')
    fields = ('name', 'email', 'phone', 'password1', 'password2', 'is_verified', 'is_block', 'join_date', 'profile_photo','referral_code')
    readonly_fields = ('join_date',)

class ReferralAdmin(admin.ModelAdmin):
    list_display = ('user', 'referral_code', 'referred_by')
    search_fields = ('user__email', 'referral_code')    

admin.site.register(Usermodels, UsermodelsAdmin)
admin.site.register(Referral, ReferralAdmin)