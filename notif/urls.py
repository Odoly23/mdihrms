from django.urls import path

from . import views

urlpatterns = [
	path('badge/', views.badge, name='notif-badge'),
	path('birthdays/', views.birthdays, name='notif-birthdays'),
]
