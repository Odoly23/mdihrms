from django.urls import path

from . import views

urlpatterns = [
	path('', views.my_claims, name='health-mine'),
	path('new/', views.claim_new, name='health-new'),
	path('all/', views.all_claims, name='health-all'),
	path('<int:pk>/cancel/', views.claim_cancel, name='health-cancel'),
	path('<int:pk>/pay/', views.claim_pay, name='health-pay'),
	path('<int:pk>/receipt/', views.receipt, name='health-receipt'),
	path('<int:pk>/<str:action>/', views.claim_decide, name='health-decide'),
]
