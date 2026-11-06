import datetime

from django.core.cache import cache
from django.utils import timezone

from attendance import qr_service as svc
from employee.models import Employee
from leave.models import Leaves

ACTIVE_STATUS = 1
CACHE_SECONDS = 300


def _is_leap(y):
	return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def birthdays_on(day):
	"""Funsionariu aktif yang berulang tahun pada tanggal `day` (29 Februari dirayakan 28 Februari di tahun biasa)."""
	key = 'notif:bday:%s' % day.isoformat()
	data = cache.get(key)
	if data is None:
		q = Employee.objects.filter(status_id=ACTIVE_STATUS, date_of_birth__month=day.month, date_of_birth__day=day.day)
		rows = list(q)
		if day.month == 2 and day.day == 28 and not _is_leap(day.year):
			rows += list(Employee.objects.filter(status_id=ACTIVE_STATUS, date_of_birth__month=2, date_of_birth__day=29))
		data = [(e.pk, '%s %s' % (e.first_name or '', e.last_name or '')) for e in rows]
		data = [(pk, ' '.join(n.split())) for pk, n in sorted(data, key=lambda x: x[1])]
		cache.set(key, data, CACHE_SECONDS)
	return data


def birthdays_of_month(year, month):
	out = {}
	for d in range(1, 32):
		try:
			day = datetime.date(year, month, d)
		except ValueError:
			break
		rows = birthdays_on(day)
		if rows:
			out[day] = rows
	return out


def pending_leaves(exclude_employee_id=None):
	qs = Leaves.objects.filter(is_active=True, is_confirm=False)
	if exclude_employee_id:
		qs = qs.exclude(employee_id=exclude_employee_id)
	return qs.count()


def today():
	return svc.to_local(timezone.now()).date()
