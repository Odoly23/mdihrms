from django.conf import settings

from attendance import qr_service as svc

from . import roles


def nav(request):
	"""Nama grup pertama (kebiasaan proyek lama) dan hak menu untuk navbar (`can.<nama>`)."""
	user = getattr(request, 'user', None)
	group = ''
	perms = {}
	if user is not None and user.is_authenticated:
		g = user.groups.all()[:1]
		group = g[0].name if g else ''
		perms = {k[:-7].lower(): roles.has_role(user, k) for k in roles._DEFAULTS}
		perms.update({
			'qr_view': svc.in_groups(user, svc.conf('VIEWER_GROUPS')),
			'qr_manage': svc.in_groups(user, svc.conf('MANAGER_GROUPS')),
			'qr_device': svc.in_groups(user, svc.conf('DEVICE_GROUPS')),
			'admin_site': user.is_staff,
		})
	return {'nav_group': group, 'can': perms,
		'lang_in_navbar': bool(getattr(settings, 'ATTENDANCE_LANG_IN_NAVBAR', False))}
