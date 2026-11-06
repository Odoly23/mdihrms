from django.conf import settings


def nav(request):
	"""Nama grup pertama pengguna (sama dengan kebiasaan proyek lama: user.groups.all.0.name)."""
	user = getattr(request, 'user', None)
	group = ''
	if user is not None and user.is_authenticated:
		g = user.groups.all()[:1]
		group = g[0].name if g else ''
	return {'nav_group': group, 'lang_in_navbar': bool(getattr(settings, 'ATTENDANCE_LANG_IN_NAVBAR', False))}
