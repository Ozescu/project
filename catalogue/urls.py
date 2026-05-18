from django.urls import path
from . import views

app_name = 'catalogue'

urlpatterns = [
    path('', views.list_view, name='list'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_form, name='category_add'),
    path('categories/<int:pk>/edit/', views.category_form, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('ouvrage/add/', views.ouvrage_form, name='ouvrage_add'),
    path('ouvrage/<int:pk>/edit/', views.ouvrage_form, name='ouvrage_edit'),
    path('ouvrage/<int:pk>/delete/', views.ouvrage_delete, name='ouvrage_delete'),
    path('ouvrage/<int:ouvrage_pk>/exemplaire/add/', views.exemplaire_form, name='exemplaire_add'),
    path('exemplaire/<int:pk>/edit/', views.exemplaire_form, name='exemplaire_edit'),
    path('exemplaire/<int:pk>/delete/', views.exemplaire_delete, name='exemplaire_delete'),
    path('<int:pk>/', views.detail_view, name='detail'),
    path('<int:pk>/favorite/', views.favorite_toggle, name='favorite_toggle'),
    path('favorites/', views.favorites_list, name='favorites'),
]
