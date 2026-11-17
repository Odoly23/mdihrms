import datetime

from django import forms

from custom.models import Institute
from employee.models import Employee
from main import ui

from .models import Sai, Tama

MAX_PDF = 10 * 1024 * 1024


def _style(form):
	for f in form.fields.values():
		w = f.widget
		w.attrs.setdefault('class', 'form-control-file' if isinstance(w, forms.ClearableFileInput) else 'form-control')


def check_pdf(f, lang):
	"""PDF sungguhan: ekstensi, ukuran <= 10 MB, dan awalan %PDF-."""
	if not f:
		return f
	if not f.name.lower().endswith('.pdf'):
		raise forms.ValidationError(ui.tr(lang, 'leave.err.pdf'))
	if f.size > MAX_PDF:
		raise forms.ValidationError(ui.tr(lang, 'kts.err.size'))
	head = f.read(5)
	f.seek(0)
	if head != b'%PDF-':
		raise forms.ValidationError(ui.tr(lang, 'leave.err.notpdf'))
	return f


class _LetterForm(forms.ModelForm):
	DATE_FIELD = ''

	def __init__(self, *args, lang='tet', today=None, **kwargs):
		super().__init__(*args, **kwargs)
		self.lang = lang
		self.today = today or datetime.date.today()
		ui.set_labels(self, lang, {'nu_ref': 'kts.f.ref', 'de': 'kts.f.from', 'para': 'kts.f.to', 'asuntu': 'kts.f.subject', 'obs': 'th.note',
			'file_pdf': 'kts.f.file', 'entrega': 'kts.f.delivery', 'institutu': 'kts.f.institute', 'institutus': 'kts.f.institute',
			'data_kartatama': 'kts.f.date_in', 'data_kartasai': 'kts.f.date_out'})
		for n in ('institutu', 'institutus'):
			if n in self.fields:
				self.fields[n].queryset = Institute.objects.order_by('name')
				self.fields[n].empty_label = ui.tr(lang, 'form.blank')
				self.fields[n].required = False
		for n in ('nu_ref', 'de', 'para', 'asuntu', self.DATE_FIELD):
			self.fields[n].required = True
		self.fields[self.DATE_FIELD].widget = forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
		_style(self)
		ui.localize_errors(self, lang)

	def _err(self, key, **kw):
		return forms.ValidationError(ui.tr(self.lang, key, **kw))

	def clean_file_pdf(self):
		return check_pdf(self.cleaned_data.get('file_pdf'), self.lang)

	def clean_nu_ref(self):
		return ' '.join((self.cleaned_data.get('nu_ref') or '').split())

	def clean(self):
		data = super().clean()
		d = data.get(self.DATE_FIELD)
		if d and (d > self.today + datetime.timedelta(days=1) or d.year < self.today.year - 5):
			self.add_error(self.DATE_FIELD, self._err('kts.err.date'))
		return data


class TamaForm(_LetterForm):
	DATE_FIELD = 'data_kartatama'

	class Meta:
		model = Tama
		fields = ['nu_ref', 'institutu', 'de', 'para', 'asuntu', 'data_kartatama', 'entrega', 'obs', 'file_pdf']

	def clean(self):
		data = super().clean()
		ref, de, d = data.get('nu_ref'), (data.get('de') or '').strip(), data.get('data_kartatama')
		if ref and de and d:
			qs = Tama.objects.filter(nu_ref__iexact=ref, de__iexact=de, data_kartatama=d)
			if self.instance.pk:
				qs = qs.exclude(pk=self.instance.pk)
			if qs.exists():
				raise self._err('kts.err.dup_in')
		return data


class SaiForm(_LetterForm):
	DATE_FIELD = 'data_kartasai'

	class Meta:
		model = Sai
		fields = ['nu_ref', 'institutus', 'de', 'para', 'asuntu', 'data_kartasai', 'obs', 'file_pdf']

	def clean(self):
		data = super().clean()
		ref, d = data.get('nu_ref'), data.get('data_kartasai')
		if ref and d:
			qs = Sai.objects.filter(nu_ref__iexact=ref, anu_letivu=str(d.year))
			if self.instance.pk:
				qs = qs.exclude(pk=self.instance.pk)
			if qs.exists():
				raise self._err('kts.err.dup_out')
		return data


class DisposeForm(forms.Form):
	handler = forms.ModelChoiceField(Employee.objects.none())
	despacho = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), max_length=2000)
	due_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))

	def __init__(self, *args, lang='tet', **kwargs):
		super().__init__(*args, **kwargs)
		ui.set_labels(self, lang, {'handler': 'kts.f.handler', 'despacho': 'kts.f.despacho', 'due_date': 'kts.f.due'})
		self.fields['handler'].queryset = Employee.objects.filter(status_id=1).order_by('first_name', 'last_name')
		self.fields['handler'].empty_label = ui.tr(lang, 'form.choose')
		_style(self)
		ui.localize_errors(self, lang)


class DoneForm(forms.Form):
	note = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), max_length=500)
	done_file = forms.FileField(required=False)

	def __init__(self, *args, lang='tet', **kwargs):
		super().__init__(*args, **kwargs)
		self.lang = lang
		ui.set_labels(self, lang, {'note': 'kts.f.result', 'done_file': 'kts.f.done_file'})
		_style(self)
		ui.localize_errors(self, lang)

	def clean_done_file(self):
		return check_pdf(self.cleaned_data.get('done_file'), self.lang)
