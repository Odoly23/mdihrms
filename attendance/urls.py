from django.urls import include, path

from . import views

urlpatterns = [
	path('', views.dash, name='attendance-dash'),
	path('qr/', include('attendance.urls_qr')),
]
