from django.shortcuts import redirect
from django.urls import path
from . import views

app_name = 'sanctions'

urlpatterns = [
    path('', lambda request: redirect('sanctions:mine'), name='index'),
    path('mine/', views.my_sanctions, name='mine'),
    path('<int:pk>/resolve/', views.resolve_sanction, name='resolve'),
    path('<int:pk>/cancel/', views.cancel_sanction, name='cancel'),
]
