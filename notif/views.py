from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from main import roles

from . import services

MONTHS = ['Janeiru', 'Fevereiru', 'Marsu', 'Abril', 'Maiu', 'Junhu', 'Julhu', 'Agostu', 'Setembru', 'Outubru',
	'Novembru', 'Dezembru']


@require_GET
def badge(request):
	"""Angka lonceng: ulang tahun hari ini + (untuk penyetuju) pedidu lisensa yang menunggu. JSON ringan, tanpa cache browser."""
	if not request.user.is_authenticated:
		return JsonResponse({'error': 'login'}, status=401)
	day = services.today()
	names = [n for _, n in services.birthdays_on(day)]
	leaves = 0
	if roles.has_role(request.user, 'LEAVE_APPROVER_GROUPS'):
		mine = roles.linked_employee(request.user)
		leaves = services.pending_leaves(mine.pk if mine else None)
	resp = JsonResponse({'value': len(names) + leaves, 'birthdays': len(names), 'names': names[:5], 'leaves': leaves})
	resp['Cache-Control'] = 'no-store'
	return resp


def birthdays(request):
	if not request.user.is_authenticated:
		return redirect_to_login(request.get_full_path())
	day = services.today()
	try:
		month = int(request.GET.get('month', day.month))
		month = month if 1 <= month <= 12 else day.month
	except ValueError:
		month = day.month
	data = services.birthdays_of_month(day.year, month)
	rows = [{'day': d, 'names': [n for _, n in people], 'is_today': d == day} for d, people in sorted(data.items())]
	return render(request, 'notif/birthdays.html', {
		'title': 'Aniversariu', 'rows': rows, 'month': month, 'monthname': MONTHS[month - 1],
		'months': list(enumerate(MONTHS, 1)), 'today': day})
