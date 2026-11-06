from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dash(request):
	"""Painel Absensia: pintu masuk ke absensi QR."""
	return render(request, 'attendance/dash.html', {'title': 'Painel Absensia', 'legend': 'Painel Absensia'})
