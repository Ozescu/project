from django.contrib import admin
from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('ouvrage', 'lecteur', 'date_reservation', 'position_file', 'statut')
    list_filter = ('statut',)
    search_fields = ('ouvrage__titre', 'lecteur__username')
from django.contrib import admin

# Register your models here.
