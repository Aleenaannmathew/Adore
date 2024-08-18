from django.contrib import admin
from .models import Banner
# Register your models here.

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'subtitle', 'created_at', 'updated_at')
    search_fields = ('title', 'subtitle')
    list_filter = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    fields = ('title', 'subtitle', 'image')
    readonly_fields = ('created_at', 'updated_at')