import datetime
import re

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from django.utils import timezone

from attendance import holidays as hol
from attendance import qr_i18n
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
	notice = None
	if user is not None and user.is_authenticated:
		notice = hol.notice(svc.to_local(timezone.now()).date(), qr_i18n.get_lang(request))
	return {'holiday_notice': notice, 'nav_group': group, 'can': perms, 'site': site_info(), 'now_year': datetime.date.today().year,
		'lang_in_navbar': bool(getattr(settings, 'ATTENDANCE_LANG_IN_NAVBAR', False))}


_SITE_KEY = 'main:site-info'
_PHONE_CLEAN = re.compile(r'[^0-9+]')


def site_info():
	"""Alamat, telepon, email untuk topbar: dari lembaga aktif (custom.Institute) bila ada, jika tidak dari
	setelan SITE_ADDRESS / SITE_PHONE / SITE_EMAIL (.env). Di-cache 5 menit; tidak ada nilai yang dikarang."""
	info = cache.get(_SITE_KEY)
	if info is None:
		from custom.models import Institute
		inst = Institute.objects.filter(is_active=True).select_related('municipality').order_by('id').first()
		name = address = phone = email = ''
		if inst:
			name = inst.name or ''
			parts = [inst.address, inst.village.name if inst.village_id else '', inst.municipality.name if inst.municipality_id else '']
			address = ', '.join(x for x in parts if x)
			phone, email = inst.phone or '', inst.email or ''
		address = address or getattr(settings, 'SITE_ADDRESS', '') or ''
		phone = phone or getattr(settings, 'SITE_PHONE', '') or ''
		email = email or getattr(settings, 'SITE_EMAIL', '') or ''
		name = name or getattr(settings, 'SITE_NAME', '') or 'Mata Dalan Institute'
		try:
			validate_email(email.strip())
			email = email.strip()
		except ValidationError:
			email = ''
		phone = phone.strip()
		info = {'name': name.strip(), 'address': address.strip(), 'phone': phone, 'email': email,
			'tel': _PHONE_CLEAN.sub('', phone)}
		cache.set(_SITE_KEY, info, 300)
	return info
