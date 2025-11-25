from django.urls import path
from .views import dashboard, buy_ticket, verify_otp, metro_map, scanner_view, login_success

urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'),
    path('buy/', buy_ticket, name='buy_ticket'),
    path('verify-otp/', verify_otp, name='verify_otp'),
    path('map/', metro_map, name='metro_map'),
    path('scanner-portal/', scanner_view, name='scanner'),
    path('login-success/', login_success, name='login_success'),
]