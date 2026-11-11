from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from main import ui


@login_required
def dash(request):
	"""Painel Absensia: pintu masuk ke absensi QR."""
	return render(request, 'attendance/dash.html', {'title': ui.tr(request, 'cfg.crumb').title(), 'legend': ui.tr(request, 'cfg.crumb')})
