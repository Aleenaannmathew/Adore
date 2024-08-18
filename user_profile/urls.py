# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('profile/',views.profile,name='profile'),
    path('edit_user_details/', views.edit_user_details, name='edit_user_details'),
    path('save-address/', views.save_address, name='address-save'),
    path('get-address/', views.get_address, name='get-address'),
    path('get-address/<int:address_id>/',views.get_edit_address, name='get_address'),
    path('update-address/<int:address_id>/', views.update_address, name='update_address'),
    path('delete-address/<int:address_id>/', views.delete_address, name='delete_address'),
    path('password_change/<int:id>/', views.password_change, name='password_change'),
    path('get_wallet_data/', views.get_wallet_data, name='get_wallet_data'),
    path('change-profile/',views.change_profile, name='change_profile'),
    path('remove-profile-picture/',views.remove_profile_picture, name='remove_profile_picture'),
]


