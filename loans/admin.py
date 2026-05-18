from django.contrib import admin
from .models import Emprunt


@admin.register(Emprunt)
class EmpruntAdmin(admin.ModelAdmin):
    list_display = ('exemplaire', 'lecteur', 'bibliothecaire', 'date_emprunt', 'date_retour_prevue', 'statut')
    list_filter = ('statut',)
    search_fields = ('exemplaire__ouvrage__titre', 'lecteur__username')
from django.contrib import admin

# Register your models here.
