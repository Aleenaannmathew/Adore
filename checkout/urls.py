from django.contrib import admin
from django.urls import path
from .views import checkout, place_order, order_success, order_details, create_razorpay_order, verify_razorpay_payment, create_wallet_order, cancel_order, return_order_item,download_invoice,handle_failed_payment,order_failed
from .views import get_order_details,handle_payment_success


urlpatterns = [
    path('checkout/', checkout, name='checkout'),
    path('place_order/', place_order, name='place_order'),
    path('create_razorpay_order/', create_razorpay_order, name='create_razorpay_order'),
    path('verify_razorpay_payment/', verify_razorpay_payment, name='verify_razorpay_payment'),
    path('order_success/<int:order_id>/', order_success, name='order_success'),
    path('order_details/<int:order_id>/', order_details, name='order_details'),
    path('cancel_order/<int:order_id>/', cancel_order, name='cancel_order'),
    path('order/return/', return_order_item, name='return_order_item'),
    path('create_wallet_order/', create_wallet_order, name='create_wallet_order'),
    path('download-invoice/<int:order_id>/', download_invoice, name='download_invoice'),
    path('handle_failed_payment/',handle_failed_payment, name='handle_failed_payment'),
    path('order_failed/<int:order_id>/', order_failed, name='order_failed'),
    path('get_order_details/<int:order_id>/', get_order_details, name='get_order_details'),
    path('handle_payment_success/', handle_payment_success, name='handle_payment_success'),
    
]   