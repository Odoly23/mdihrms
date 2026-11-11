from django.urls import include, path

from . import views, views_config as cfg

urlpatterns = [
	path('', views.dash, name='attendance-dash'),
	path('qr/', include('attendance.urls_qr')),
	# konfigurasaun (nama URL sama dengan aplikasi absensi lama)
	path('config/', cfg.dash, name='attendance-custom-dash'),
	path('config/year/add/', cfg.year_add, name='attendance-custom-year-add'),
	path('config/year/<int:pk>/', cfg.year_set, name='attendance-custom-year'),
	path('config/month/<int:pk>/', cfg.month_set, name='attendance-custom-month'),
	path('config/status/add/', cfg.status_add, name='attendance-custom-status-add'),
	path('config/status/<int:pk>/', cfg.status_update, name='attendance-custom-status-update'),
	path('config/holiday/', cfg.holiday_list, name='attendance-custom-holiday-list'),
	path('config/holiday/add/', cfg.holiday_add, name='attendance-custom-holiday-add'),
	path('config/holiday/<int:pk>/', cfg.holiday_update, name='attendance-custom-holiday-update'),
	path('config/tolerance/', cfg.tolerance_list, name='attendance-custom-tolerance-list'),
	path('config/tolerance/add/', cfg.tolerance_add, name='attendance-custom-tolerance-add'),
	path('config/tolerance/<int:pk>/', cfg.tolerance_update, name='attendance-custom-tolerance-update'),
]
