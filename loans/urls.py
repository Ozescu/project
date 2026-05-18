from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
	path('', views.list_loans, name='list'),
	path('create/', views.create_loan, name='create'),
	path('requests/', views.list_requests, name='requests'),
	path('request/<int:ouvrage_id>/', views.request_loan, name='request'),
	path('requests/<int:pk>/approve/', views.approve_request, name='approve_request'),
	path('requests/<int:pk>/reject/', views.reject_request, name='reject_request'),
	path('requests/<int:pk>/cancel/', views.cancel_request, name='cancel_request'),
	path('return/<int:pk>/', views.process_return, name='return'),
]
