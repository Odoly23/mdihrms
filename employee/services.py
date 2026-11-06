import hashlib

from django.contrib.auth.models import Group, User
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

from attendance.models_qr import QRCard

from .models import (ContactInfo, Employee, EmployeeDivision, EmployeePosition, EmployeeUser, IDFNumber, LocationTL,
	Photo)

_PASSWORD_CHARS = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'   # tanpa karakter yang mirip


def _unique_username(base):
	name, n = base[:140], 1
	while User.objects.filter(username__iexact=name).exists():
		n += 1
		name = '%s%d' % (base[:130], n)
	return name


@transaction.atomic
def save_employee(form, by_user, create_account=False):
	"""Simpan Employee beserta NRF, posisi, diresaun, kontak, foto. Funsionariu baru otomatis mendapat kartu QR
	(dan, bila diminta, akun login dengan kata sandi acak yang ditampilkan sekali). Mengembalikan (employee, akun)."""
	d = form.cleaned_data
	e = form.save(commit=False)
	new = e.pk is None
	now = timezone.now()
	if new:
		e.datetime, e.user = now, by_user
	e.save()
	if not e.hashed:
		e.hashed = hashlib.md5(str(e.pk).encode()).hexdigest()
		e.save(update_fields=['hashed'])
	if d['nrf'] or IDFNumber.objects.filter(employee=e).exists():
		IDFNumber.objects.update_or_create(employee=e, defaults={'nrf': d['nrf'] or None, 'datetime': now, 'user': by_user})
	EmployeePosition.objects.update_or_create(employee=e, defaults={'position': d['position']})
	EmployeeDivision.objects.update_or_create(employee=e, defaults={
		'dg': d['dg'], 'division': d['division'], 'department': d['department'], 'section': d['section']})
	if d['phone'] or d['email'] or ContactInfo.objects.filter(employee=e).exists():
		ContactInfo.objects.update_or_create(employee=e, defaults={
			'phone': d['phone'] or None, 'email': d['email'] or None, 'datetime': now, 'user': by_user})
	if d.get('image'):
		ph, _ = Photo.objects.get_or_create(employee=e, defaults={'datetime': now, 'user': by_user})
		ph.image = d['image']
		ph.datetime = now
		ph.save()
	account = None
	if new:
		QRCard.objects.get_or_create(employee=e, defaults={'datetime': now, 'user': by_user})
		if create_account:
			password = get_random_string(10, _PASSWORD_CHARS)
			u = User.objects.create_user(_unique_username(d['nrf'] or 'emp%d' % e.pk), password=password)
			u.groups.add(Group.objects.get_or_create(name='funsionario')[0])
			EmployeeUser.objects.create(employee=e, user=u)
			account = (u.username, password)
	return e, account


@transaction.atomic
def save_address(emp, form, by_user):
	d = form.cleaned_data
	LocationTL.objects.update_or_create(employee=emp, defaults={
		'municipality': d['municipality'], 'administrativepost': d['administrativepost'], 'village': d['village'],
		'aldeia': d['aldeia'] or None, 'datetime': timezone.now(), 'user': by_user})
