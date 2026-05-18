from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
	fieldsets = DjangoUserAdmin.fieldsets + (
		('Informations', {'fields': ('role', 'telephone', 'adresse', 'statut_compte', 'is_suspended')}),
	)
	list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'statut_compte', 'is_suspended')
	list_filter = ('role', 'statut_compte', 'is_suspended')
	search_fields = ('username', 'email', 'first_name', 'last_name')
