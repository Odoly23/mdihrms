from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from main import views as main_views

admin.site.site_header = 'MDI-HRMS SUPER USER'

urlpatterns = [
	path('admin/', admin.site.urls),
	path('', auth_views.LoginView.as_view(template_name='home/login.html', redirect_authenticated_user=True), name='login'),
	path('login/', auth_views.LoginView.as_view(template_name='home/login.html', redirect_authenticated_user=True), name='login'),
	path('logout/', auth_views.LogoutView.as_view(), name='logout'),
	path('home/', main_views.home, name='home'),
	path('attendance/', include('attendance.urls')),
	path('leave/', include('leave.urls')),
	path('kolokasaun/', include('contract.urls')),
	path('funsionariu/', include('employee.urls')),
	path('assets/', include('assets.urls')),
	path('health/', include('health.urls')),
	path('notif/', include('notif.urls')),
	path('custom/', include('custom.urls')),
]

if settings.DEBUG:
	urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = 'main.views.error_403'
handler404 = 'main.views.error_404'
handler500 = 'main.views.error_500'
