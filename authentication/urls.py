from django.contrib import admin
from django.urls import path
from .import views


urlpatterns = [
    path('',views.home,name='home'),
    path('login/',views.user_login,name='login'),
    path('register/',views.register,name='register'),
    path('forget-password/', views.forget_pass, name='forget_password'),
    path('change_password/<int:id>/', views.change_password, name='change_password'),
    path('otp/<int:id>/<str:purpose>/', views.otp, name='otp'),
    path('resend_otp/<int:id>/',views.resend_otp,name='resend_otp'),
    path('logout/',views.user_logout,name='logout'),

  


]
