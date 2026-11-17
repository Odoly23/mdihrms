from django.urls import path

from . import views

urlpatterns = [
	path('', views.dash, name='kts-dash'),
	path('tama/', views.tama_list, name='kts-tama'),
	path('tama/new/', views.tama_add, name='kts-tama-add'),
	path('tama/mine/', views.tama_mine, name='kts-tama-mine'),
	path('tama/<int:pk>/', views.tama_detail, name='kts-tama-detail'),
	path('tama/<int:pk>/edit/', views.tama_edit, name='kts-tama-edit'),
	path('tama/<int:pk>/approve/', views.tama_approve, name='kts-tama-approve'),
	path('tama/<int:pk>/return/', views.tama_return, name='kts-tama-return'),
	path('tama/<int:pk>/dispose/', views.tama_dispose, name='kts-tama-dispose'),
	path('tama/<int:pk>/done/', views.tama_done, name='kts-tama-done'),
	path('tama/<int:pk>/file/', views.tama_file, name='kts-tama-file'),
	path('tama/<int:pk>/file/<str:which>/', views.tama_file, name='kts-tama-file-which'),
	path('sai/', views.sai_list, name='kts-sai'),
	path('sai/new/', views.sai_add, name='kts-sai-add'),
	path('sai/<int:pk>/', views.sai_detail, name='kts-sai-detail'),
	path('sai/<int:pk>/edit/', views.sai_edit, name='kts-sai-edit'),
	path('sai/<int:pk>/file/', views.sai_file, name='kts-sai-file'),
]
