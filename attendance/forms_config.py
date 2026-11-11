import datetime

from django import forms

from main import ui

from .models import AttendanceStatus, NacionalHoliday, Tolerance, Year

# sigla yang dipakai absensi QR (hadir, alpa, lisensa): tidak boleh diganti
LOCKED_CODES = ('P', 'F', 'L')


class _Base(forms.ModelForm):
	LABELS = {}

	def __init__(self, *args, lang='tet', **kwargs):
		super().__init__(*args, **kwargs)
		self.lang = lang
		ui.set_labels(self, lang, self.LABELS)
		for f in self.fields.values():
			f.widget.attrs.setdefault('class', 'form-check-input' if isinstance(f.widget, forms.CheckboxInput) else 'form-control')

	def _err(self, key, **kw):
		return forms.ValidationError(ui.tr(self.lang, key, **kw))


class YearForm(_Base):
	LABELS = {'year': 'f.year'}

	class Meta:
		model = Year
		fields = ['year']

	def clean_year(self):
		y = self.cleaned_data['year']
		if y is None or not 2000 <= y <= 2100:
			raise self._err('cfg.err.year')
		if Year.objects.filter(year=y).exists():
			raise self._err('cfg.err.year_dup')
		return y


class AttendanceStatusForm(_Base):
	LABELS = {'code': 'f.code', 'name': 'th.name'}

	class Meta:
		model = AttendanceStatus
		fields = ['code', 'name']

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.locked = bool(self.instance.pk and self.instance.code in LOCKED_CODES)
		self.fields['code'].required = True
		self.fields['name'].required = True
		if self.locked:
			self.fields['code'].disabled = True                      # nilai asli dipakai, kiriman klien diabaikan

	def clean_code(self):
		code = (self.cleaned_data.get('code') or '').strip()
		if self.locked:
			return self.instance.code
		if code.upper() in LOCKED_CODES and not (self.instance.pk and self.instance.code == code):
			raise self._err('cfg.err.code_locked', code=code.upper())
		qs = AttendanceStatus.objects.filter(code__iexact=code)
		if self.instance.pk:
			qs = qs.exclude(pk=self.instance.pk)
		if qs.exists():
			raise self._err('cfg.err.code_dup')
		return code


class _DateForm(_Base):
	"""Dasar untuk feriadu dan tolerânsia: tanggal wajib, tidak ganda."""
	LABELS = {'name': 'th.name', 'date': 'f.date', 'is_active': 'f.active'}
	MODEL = None
	# BooleanField(null=True) di model menghasilkan pilihan Ya/Tidak/Tak tahu; di sini kotak centang biasa (kosong = nonaktif)
	is_active = forms.BooleanField(required=False, initial=True)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['date'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d')
		self.fields['name'].required = True
		self.fields['is_active'].initial = True

	def _scope(self):
		return self.MODEL.objects.all()

	MIN_YEAR = 2000                                   # hari toleransi: tahun berjalan; libur nasional: tahun peristiwa boleh lama

	def clean_date(self):
		d = self.cleaned_data['date']
		if not self.MIN_YEAR <= d.year <= 2100:
			raise self._err('cfg.err.date_range' if self.MIN_YEAR < 2000 else 'cfg.err.year')
		qs = self._scope().filter(date=d)
		if self.instance.pk:
			qs = qs.exclude(pk=self.instance.pk)
		if qs.exists():
			raise self._err('cfg.err.date_dup')
		return d


class NacionalHolidayForm(_DateForm):
	MODEL = NacionalHoliday
	MIN_YEAR = 1900

	class Meta:
		model = NacionalHoliday
		fields = ['name', 'date', 'is_active']


class ToleranceForm(_DateForm):
	MODEL = Tolerance

	class Meta:
		model = Tolerance
		fields = ['name', 'date', 'is_active']

	def _scope(self):
		return Tolerance.objects.filter(year=self.year) if getattr(self, 'year', None) else Tolerance.objects.none()

	def __init__(self, *args, year=None, **kwargs):
		self.year = year
		super().__init__(*args, **kwargs)
