from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
	return render(request, 'main/home.html', {'title': 'Varanda'})


def error_403(request, exception=None):
	return render(request, 'home/403.html', status=403)


def error_404(request, exception=None):
	return render(request, 'home/404.html', status=404)


def error_500(request):
	return render(request, 'home/500.html', status=500)
