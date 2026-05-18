from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    path('reserve/<int:ouvrage_id>/', views.reserve_ouvrage, name='reserve'),
    path('confirm/<int:pk>/', views.confirm_reservation, name='confirm'),
    path('reject/<int:pk>/', views.reject_reservation, name='reject'),
    path('cancel/<int:pk>/', views.cancel_reservation, name='cancel'),
    path('mine/', views.my_reservations, name='my_reservations'),
]
