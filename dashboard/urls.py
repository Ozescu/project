from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('admin/', views.admin_dashboard, name='admin'),
    path('biblio/', views.biblio_dashboard, name='biblio'),
    path('lecteur/', views.reader_dashboard, name='reader'),
    path('permissions/', views.system_permissions, name='permissions'),
    path('notifications/settings/', views.notification_settings, name='notification_settings'),
    path('sanctions/settings/', views.sanction_settings, name='sanction_settings'),
    path('reports/', views.system_reports, name='system_reports'),
]
