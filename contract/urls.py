from django.urls import path

from . import views

urlpatterns = [
	path('', views.placement_list, name='placement-list'),
	path('<int:emp_id>/', views.placement_history, name='placement-history'),
	path('<int:emp_id>/new/', views.placement_new, name='placement-new'),
]
