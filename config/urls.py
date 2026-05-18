"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from dashboard.views import landing_view

urlpatterns = [

    path('', landing_view, name='landing'),

    path('admin/', admin.site.urls),

    path(
        'accounts/',
        include('accounts.urls', namespace='accounts')
    ),

    path(
        'catalogue/',
        include('catalogue.urls', namespace='catalogue')
    ),

    path(
        'loans/',
        include('loans.urls', namespace='loans')
    ),

    path(
        'reservations/',
        include('reservations.urls', namespace='reservations')
    ),

    path(
        'sanctions/',
        include('sanctions.urls', namespace='sanctions')
    ),

    path(
        'notifications/',
        include('notifications.urls', namespace='notifications')
    ),

    path(
        'dashboard/',
        include('dashboard.urls', namespace='dashboard')
    ),

    path(
        'recommendations/',
        include('recommendations.urls', namespace='recommendations')
    ),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )