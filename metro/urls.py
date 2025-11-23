from django.urls import path
from . import views



urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('buy/', views.buy_ticket, name='buy_ticket'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('scan/', views.scanner_view, name='scanner'),
    path('stats/', views.admin_stats, name='admin_stats'),
    
    # New Map URL
    path('map/', views.metro_map, name='metro_map'),
]