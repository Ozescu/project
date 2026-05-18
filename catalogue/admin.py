from django.contrib import admin
from .models import Categorie, Ouvrage, Exemplaire


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('nom',)


@admin.register(Ouvrage)
class OuvrageAdmin(admin.ModelAdmin):
    list_display = ('titre', 'auteur', 'isbn', 'categorie')
    search_fields = ('titre', 'auteur', 'isbn', 'sujet')


@admin.register(Exemplaire)
class ExemplaireAdmin(admin.ModelAdmin):
    list_display = ('ouvrage', 'code', 'status')
    list_filter = ('status',)
from django.contrib import admin

# Register your models here.
