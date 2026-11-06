"""Bantuan bahasa untuk halaman di luar absensi QR (memakai kamus yang sama: attendance/qr_i18n*.py)."""
from attendance import qr_i18n as i18n


def lang(request):
	return i18n.get_lang(request)


def tr(request_or_lang, key, **params):
	code = request_or_lang if isinstance(request_or_lang, str) else i18n.get_lang(request_or_lang)
	return i18n.tr(code, key, **params)


def set_labels(form, code, labels):
	"""Ganti label field form sesuai bahasa: labels = {'nama_field': 'kunci.terjemahan'}."""
	for name, key in labels.items():
		if name in form.fields:
			form.fields[name].label = i18n.tr(code, key)


def choice_labels(field, code, values, blank=True):
	"""Pilihan dengan nilai tetap (disimpan apa adanya) tetapi teks tampil diterjemahkan (kunci 'ch.<nilai>')."""
	rows = [(v, i18n.tr(code, 'ch.' + v)) for v in values]
	field.choices = ([('', '---------')] if blank else []) + rows
