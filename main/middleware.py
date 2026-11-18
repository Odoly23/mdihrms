from django.core.cache import cache
from django.shortcuts import redirect

_EXEMPT = ('/static/', '/account/password/', '/logout/', '/login/', '/notif/badge/')


def _key(uid):
	return 'mdi:mustchange:%d' % uid


def must_change(uid):
	"""Apakah akun wajib mengganti kata sandi. Di-cache 5 menit; reset dan penggantian kata sandi memperbarui cache seketika."""
	v = cache.get(_key(uid))
	if v is None:
		from .models import MustChangePassword
		v = MustChangePassword.objects.filter(user_id=uid).exists()
		cache.set(_key(uid), v, 300)
	return v


def set_flag(uid, on):
	cache.set(_key(uid), bool(on), 300)


class ForcePasswordChange:
	"""Pengguna yang kata sandinya direset admin hanya boleh membuka halaman ganti kata sandi (dan keluar)."""

	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		u = getattr(request, 'user', None)
		if u is not None and u.is_authenticated and not request.path.startswith(_EXEMPT) and must_change(u.pk):
			return redirect('password-change')
		return self.get_response(request)
