import datetime

from django import forms

from main import ui

from .models import Leaves, LeaveType

MAX_DAYS = 90
MAX_BACKDATE_DAYS = 30
MAX_FILE_BYTES = 5 * 1024 * 1024


class LeaveRequestForm(forms.Form):
	leave_type = forms.ModelChoiceField(LeaveType.objects.all())
	start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
	end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
	file = forms.FileField(required=False)

	def __init__(self, *args, employee=None, today=None, lang='tet', **kwargs):
		super().__init__(*args, **kwargs)
		self.employee = employee
		self.lang = lang
		self.today = today or datetime.date.today()
		ui.set_labels(self, lang, {'leave_type': 'leave.f.type', 'start_date': 'leave.f.start',
			'end_date': 'leave.f.end', 'file': 'leave.f.file'})
		self.fields['leave_type'].empty_label = ui.tr(lang, 'form.choose')
		self.fields['leave_type'].label_from_instance = lambda lt: ui.std_name(lt, lang)
		ui.localize_errors(self, lang)
		for f in self.fields.values():
			f.widget.attrs.setdefault('class', 'form-control')

	def _err(self, key, **kw):
		return forms.ValidationError(ui.tr(self.lang, key, **kw))

	def clean_file(self):
		f = self.cleaned_data.get('file')
		if f:
			if not f.name.lower().endswith('.pdf'):
				raise self._err('leave.err.pdf')
			if f.size > MAX_FILE_BYTES:
				raise self._err('leave.err.size')
			if f.read(5) != b'%PDF-':
				raise self._err('leave.err.notpdf')
			f.seek(0)
		return f

	def clean(self):
		data = super().clean()
		s, e = data.get('start_date'), data.get('end_date')
		if s and e:
			if e < s:
				raise self._err('leave.err.order')
			if (e - s).days + 1 > MAX_DAYS:
				raise self._err('leave.err.max', n=MAX_DAYS)
			if s < self.today - datetime.timedelta(days=MAX_BACKDATE_DAYS):
				raise self._err('leave.err.back', n=MAX_BACKDATE_DAYS)
			if self.employee and Leaves.objects.filter(
					employee=self.employee, is_active=True, start_date__lte=e, end_date__gte=s).exists():
				raise self._err('leave.err.overlap')
		return data
