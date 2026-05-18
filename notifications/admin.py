from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('lecteur', 'type_notification', 'date_envoi', 'lu')
    list_filter = ('type_notification', 'lu')
    search_fields = ('lecteur__username', 'message')
from django.contrib import admin

# Register your models here.
