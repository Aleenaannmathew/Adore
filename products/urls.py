from django.contrib import admin
from django.urls import path
from .views import show_allproducts,shop_details,variant_images_ajax, get_variants, submit_comment


urlpatterns = [
    path('showproduct/', show_allproducts, name='showproducts'),
    path('product/<slug:product_slug>/', shop_details, name='shop_details'),
    path('ajax/variant-images/<int:variant_id>/', variant_images_ajax, name='variant_images_ajax'),
    path('get-variants/', get_variants, name='get_variants'),
    path('submit-comment/', submit_comment, name='submit_comment'),

    
  


]   