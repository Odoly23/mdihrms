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


_STD_NAMES = {('F', 'Falta'): 'legend.absent', ('P', 'Presensa'): 'legend.present', ('L', 'Lisensa'): 'legend.leave'}


def std_name(obj, lang):
	"""Nama status absensia / tipe lisensa; nama bawaan Tetun (mdi_setup) diterjemahkan, nama buatan admin dipertahankan."""
	name = (getattr(obj, 'name', '') or '').strip()
	key = _STD_NAMES.get(((getattr(obj, 'code', '') or '').strip().upper(), name))
	return i18n.tr(lang, key) if key else name


def localize_errors(form, lang):
	"""Pesan galat bawaan Django (Inggris) diganti ke bahasa pengguna: wajib diisi, nilai/tanggal/angka/gambar salah, terlalu panjang."""
	from django import forms
	from django.core import validators
	for field in form.fields.values():
		em = field.error_messages
		em['required'] = i18n.tr(lang, 'err.required')
		if isinstance(field, forms.ModelChoiceField):
			em['invalid_choice'] = i18n.tr(lang, 'err.invalid_choice')
		elif isinstance(field, forms.ChoiceField):
			em['invalid_choice'] = i18n.tr(lang, 'err.invalid_choice')
		if isinstance(field, forms.DateField):
			em['invalid'] = i18n.tr(lang, 'err.invalid_date')
		elif isinstance(field, forms.IntegerField):
			em['invalid'] = i18n.tr(lang, 'err.invalid_number')
		elif isinstance(field, forms.ImageField):
			em['invalid_image'] = i18n.tr(lang, 'err.invalid_image')
		else:
			em['invalid'] = i18n.tr(lang, 'err.invalid')
		for v in field.validators:
			if isinstance(v, validators.MaxLengthValidator):
				v.message = i18n.tr(lang, 'err.max_length', max='%(limit_value)s')
