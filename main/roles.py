"""Hak akses per grup untuk fitur di luar absensi QR (lisensa, kolokasaun, daftar funsionariu).
Setiap daftar bisa diganti di settings.py dengan MDI_<NAMA>, mis. MDI_LEAVE_APPROVER_GROUPS = ['admin'].

Ringkasan peran:
  admin      semua hak; satu-satunya yang membuka PC kiosk, mengelola kartu QR, menambah/mengubah funsionariu
  president  (direktur) melihat rekap bulanan, menyetujui lisensa, mengalokasikan staf ke posisi
  hr         melihat semua data dan daftar staf (hanya baca)
  staff      melihat data absensi (hanya baca), mengajukan lisensa sendiri
  funsionario / employee   laporan absensi sendiri, mengajukan lisensa sendiri
"""
from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import render

_DEFAULTS = {
	'LEAVE_REQUEST_GROUPS': ['admin', 'staff', 'president', 'hr', 'funsionario', 'employee'],
	'LEAVE_APPROVER_GROUPS': ['admin', 'president'],
	'LEAVE_VIEW_ALL_GROUPS': ['admin', 'president', 'hr'],
	'PLACEMENT_EDIT_GROUPS': ['admin', 'president'],
	'PLACEMENT_VIEW_GROUPS': ['admin', 'president', 'hr', 'staff'],
	'DIRECTORY_GROUPS': ['admin', 'president', 'hr'],
	'ATTENDANCE_CONFIG_GROUPS': ['admin'],        # tinan/fulan aktif, status absensi, feriadu, tolerânsia
	'EMPLOYEE_EDIT_GROUPS': ['admin'],            # tambah/ubah data funsionariu dan membuat akun login-nya
}


def names(key):
	return getattr(settings, 'MDI_' + key, _DEFAULTS[key])


def has_role(user, key):
	if not getattr(user, 'is_authenticated', False):
		return False
	mine = getattr(user, '_mdi_group_names', None)
	if mine is None:
		mine = user._mdi_group_names = set(user.groups.values_list('name', flat=True))
	return bool(mine & set(names(key)))


def role_required(key):
	def deco(fn):
		@wraps(fn)
		def inner(request, *a, **kw):
			if not request.user.is_authenticated:
				return redirect_to_login(request.get_full_path())
			if not has_role(request.user, key):
				return render(request, 'home/403.html', status=403)
			return fn(request, *a, **kw)
		return inner
	return deco


def linked_employee(user):
	"""Pegawai yang tertaut ke akun (employee.EmployeeUser), atau None."""
	from employee.models import EmployeeUser
	link = EmployeeUser.objects.filter(user=user).select_related('employee').first()
	return link.employee if link else None
