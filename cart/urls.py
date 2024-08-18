from django.contrib import admin
from django.urls import path
from .views import shop_cart,add_to_cart, update_cart_items, remove_cart_item


urlpatterns = [
    path('showcart/', shop_cart, name='showcart'),
    path('add-to-cart/<int:variant_id>/', add_to_cart, name='add_to_cart'),
    path('update-cart-item/', update_cart_items, name='update-cart-item'),
    path('remove-cart-item/', remove_cart_item, name='remove-cart-item'),
  


]