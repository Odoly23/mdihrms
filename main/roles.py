"""Hak akses per grup untuk fitur di luar absensi QR. Empat grup (lihat main/groups.py):
  admin           admin sistem: kontrol penuh; menyetujui klaim health care milik direktur
  director        direktur: melihat semua data; menyetujui lisensa dan klaim health care; mendisposisi surat masuk; menyetujui surat keluar
  administrasaun  administrasi: membagi aset, mengurus health care (dibayar), memverifikasi surat masuk dan surat keluar
  staff           staf dan resepsionis: melihat datanya sendiri, mengajukan lisensa, mendaftarkan surat masuk, membuat surat keluar
Setiap daftar bisa diganti di settings.py dengan MDI_<NAMA>, mis. MDI_LEAVE_APPROVER_GROUPS = ['admin'].
"""
from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import render

_ALL = ['admin', 'director', 'administrasaun', 'staff']
_SEE_ALL = ['admin', 'director', 'administrasaun']

_DEFAULTS = {
	'LEAVE_REQUEST_GROUPS': _ALL,
	'LEAVE_APPROVER_GROUPS': ['admin', 'director'],
	'LEAVE_VIEW_ALL_GROUPS': _SEE_ALL,
	'PLACEMENT_EDIT_GROUPS': ['admin', 'director'],
	'PLACEMENT_VIEW_GROUPS': _ALL,
	'DIRECTORY_GROUPS': _SEE_ALL,                      # daftar staf per grup/jabatan dan detailnya
	'ASSET_MANAGER_GROUPS': ['admin', 'administrasaun'],   # mendaftarkan, menyerahkan, menerima kembali, merapikan di rak
	'ASSET_VIEW_ALL_GROUPS': _SEE_ALL,
	'ASSET_SELF_GROUPS': _ALL,
	'HEALTH_REQUEST_GROUPS': _ALL,
	'HEALTH_APPROVER_GROUPS': ['director'],            # direktur menyetujui klaim staf; admin tidak bisa mengubah keputusan
	'HEALTH_DIRECTOR_APPROVER_GROUPS': ['admin'],       # klaim milik direktur hanya disetujui admin sistem
	'HEALTH_PAYER_GROUPS': ['admin', 'administrasaun'], # administrasi mengurus pembayaran klaim yang sudah disetujui
	'HEALTH_VIEW_ALL_GROUPS': _SEE_ALL,
	'KTS_REGISTER_GROUPS': ['staff'],                  # staf (termasuk resepsionis) mendaftarkan surat masuk
	'KTS_VERIFY_GROUPS': ['administrasaun', 'admin'],  # administrasi memverifikasi surat masuk dan surat keluar
	'KTS_DISPOSE_GROUPS': ['director', 'admin'],       # direktur: disposisi/despacho surat masuk dan persetujuan surat keluar
	'KTS_VIEW_ALL_GROUPS': _SEE_ALL,
	'KTS_OUT_GROUPS': _ALL,                            # semua grup boleh membuat surat keluar
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
