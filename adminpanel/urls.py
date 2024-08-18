from django.urls import path
from django.contrib import admin
from .views import adminlogin, admin_dashboard,category,customers,add_category,products,add_products,adminlogout,toggle_user_block,toggle_category
from .views import edit_category, edit_products,edit_product_image,toggle_product_active,variants,edit_variant,add_variant,variant_image_view,edit_variantimage
from .views import toggle_variant_active,toggle_variantimage_active,coupon,addcoupon,toggle_coupon,edit_coupon,orders,order_view,update_order_status,sales_report, update_return_status, get_return_requested_items, product_offer_view,toggle_offer_active,category_offer_view,toggle_category_offer_active,bestseller,delete_offer,delete_category_offer
from .views import edit_offer_view,edit_category_offer_view,banner_list, edit_banner, toggle_banner_active, add_banner

urlpatterns = [
    path('admin/', admin.site.urls),  # Django admin
    path('custom-admin/login/', adminlogin, name='adminlogin'),
    path('custom-admin/dashboard/', admin_dashboard, name='admin_dashboard'),

    #category
    path('category/', category, name='category'),
    path('toggle/<int:category_id>/',toggle_category, name='toggle_category'),
    path('add_category/', add_category, name='add_category'),
    path('edit_category/<int:category_id>/',edit_category, name='edit_category'),

    #customers
    path('customers/', customers, name='customers'),
    path('toggle_user_block/<int:user_id>/', toggle_user_block, name='toggle_user_block'),

    #products
    path('products/', products, name='products'),
    path('add_products/', add_products, name='add_products'),
    path('edit_products/<int:product_id>/',edit_products, name='edit_products'),
    path('edit_image/<int:product_id>/', edit_product_image, name='edit_product_image'),
    path('toggle_product_active/<int:product_id>/', toggle_product_active, name='toggle_product_active'),

    #variants
    path('variants/<int:product_id>/', variants, name='variants'),
    path('edit_variant/<int:variant_id>/',edit_variant, name='edit_variant'),
    path('add_variant/<int:product_id>',add_variant,name='add_variant'),
    path('variant_imageview/<int:variant_id>/', variant_image_view, name='variant_image_view' ),
    path('edit_variantimage/<int:variant_id>', edit_variantimage, name='edit_variantimage' ),
    path('toggle_variant_active/<int:variant_id>', toggle_variant_active, name='toggle_variant_active'),
    path('toggle_variantimage_active/<int:variantimage_id>/', toggle_variantimage_active, name='toggle_variantimage_active'),

    #coupons
    path('coupon/', coupon, name='coupon'),
    path('addcoupon/', addcoupon, name='addcoupon'),
    path('editcoupon/<int:coupon_id>', edit_coupon, name='edit_coupon'),
    path('toggle_coupon_active/<int:coupon_id>/', toggle_coupon, name='toggle_coupon_active'),

    #orders
    path('orders/', orders, name='orders'),
    path('order_view/<int:order_id>/', order_view, name='order_view'),
    path('/admin/order/status/', update_order_status, name='update_order_status'),
    path('update-return-status/', update_return_status, name='update_return_status'),
    path('product-return-requests/', get_return_requested_items, name='product_return_requests'),

    #banner
    path('banners/', banner_list, name='banner_list'),
    path('banner/add/', add_banner, name='add_banner'),
    path('banner/edit/<int:pk>/', edit_banner, name='edit_banner'),
    path('banner/toggle/<int:pk>/', toggle_banner_active, name='toggle_banner_active'),
    
    path('bestsellers/', bestseller, name='bestsellers'),

    path('sales_report/', sales_report, name='sales_report'),

    #offers
    path('category-offers/', category_offer_view, name='category_offers'),
    path('category-offers/toggle-category-offer/<int:offer_id>/', toggle_category_offer_active, name='toggle_category_offer_active'),
    path('category-offers/delete-category-offer/<int:offer_id>/', delete_category_offer, name='delete_category_offer'),
    path('category-offers/edit-category-offer/<int:offer_id>/', edit_category_offer_view, name='edit_category_offer'),

    path('offers/', product_offer_view, name='product_offers'),
    path('offers/toggle/<int:offer_id>/', toggle_offer_active, name='toggle_offer_active'),
    path('offers/delete/<int:offer_id>/', delete_offer, name='delete_offer'),
    path('offers/edit/<int:offer_id>/', edit_offer_view, name='edit_offer'),


    path('adminlogout/', adminlogout, name='adminlogout' ),
   
    
    
]

