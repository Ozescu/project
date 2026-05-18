from django.contrib import admin
from .models import Sanction


@admin.register(Sanction)
class SanctionAdmin(admin.ModelAdmin):
    list_display = ('lecteur', 'type_sanction', 'montant', 'date_debut', 'date_fin', 'statut')
    list_filter = ('type_sanction', 'statut')
    search_fields = ('lecteur__username',)
from django.contrib import admin

# Register your models here.
