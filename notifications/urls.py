from django.shortcuts import redirect
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', lambda request: redirect('notifications:mine'), name='index'),
    path('mine/', views.my_notifications, name='mine'),
    path('<int:pk>/read/', views.mark_read, name='mark_read'),
    path('read-all/', views.mark_all_read, name='mark_all_read'),
]
