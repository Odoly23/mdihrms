from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from . import ui


@login_required
def home(request):
	from attendance import holidays
	from notif import services
	today = services.today()
	lang = ui.lang(request)
	names = [n for _, n in services.birthdays_on(today)]
	items = [holidays.describe(i, lang) for i in holidays.upcoming(today, days=90, limit=5)]
	return render(request, 'main/home.html', {'title': ui.tr(lang, 'ui.nav.home').title(), 'birthdays': names,
		'holidays': items, 'holiday_days': 90})


def error_403(request, exception=None):
	return render(request, 'home/403.html', status=403)


def error_404(request, exception=None):
	return render(request, 'home/404.html', status=404)


def error_500(request):
	return render(request, 'home/500.html', status=500)
