from django.urls import path

from . import views

urlpatterns = [
	path('', views.my_list, name='leave-mine'),
	path('new/', views.new, name='leave-new'),
	path('<int:pk>/cancel/', views.cancel, name='leave-cancel'),
	path('all/', views.all_list, name='leave-all'),
	path('<int:pk>/<str:action>/', views.decide, name='leave-decide'),
]
