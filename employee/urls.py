from django.urls import path

from . import views

urlpatterns = [
	path('', views.staff_list, name='staff-list'),
	path('new/', views.employee_add, name='employee-add'),
	path('<int:emp_id>/', views.staff_detail, name='staff-detail'),
	path('<int:emp_id>/edit/', views.employee_edit, name='employee-edit'),
	path('<int:emp_id>/address/', views.employee_address, name='employee-address'),
]
