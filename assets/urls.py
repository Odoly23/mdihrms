from django.urls import path

from . import views

urlpatterns = [
	path('', views.asset_list, name='asset-list'),
	path('new/', views.asset_add, name='asset-add'),
	path('mine/', views.my_assets, name='asset-mine'),
	path('survey/', views.survey, name='asset-survey'),
	path('survey.csv', views.survey_csv, name='asset-survey-csv'),
	path('<int:pk>/', views.asset_detail, name='asset-detail'),
	path('<int:pk>/edit/', views.asset_edit, name='asset-edit'),
	path('<int:pk>/assign/', views.action_assign, name='asset-assign'),
	path('<int:pk>/return/', views.action_return, name='asset-return'),
	path('<int:pk>/status/', views.action_status, name='asset-status'),
	path('<int:pk>/shelf/', views.action_shelf, name='asset-shelf'),
	path('<int:pk>/confirm/', views.action_confirm, name='asset-confirm'),
	path('<int:pk>/me/status/', views.self_status, name='asset-self-status'),
	path('<int:pk>/me/confirm/', views.self_confirm, name='asset-self-confirm'),
]
