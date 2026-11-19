from django.urls import path

from . import views

urlpatterns = [
	path('', views.account, name='account'),
	path('password/', views.password_change, name='password-change'),
]
