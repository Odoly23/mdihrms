from django.urls import path

from . import views

urlpatterns = [
	path('ajax/load-posts/', views.load_post, name='ajax_load_post'),
	path('ajax/load-villages/', views.load_village, name='ajax_load_village'),
]
