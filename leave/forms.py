import datetime

from django import forms

from .models import Leaves, LeaveType

MAX_DAYS = 90
MAX_BACKDATE_DAYS = 30
MAX_FILE_BYTES = 5 * 1024 * 1024


class LeaveRequestForm(forms.Form):
	leave_type = forms.ModelChoiceField(LeaveType.objects.all(), label="Tipu Lisensa", empty_label="-- Hili --")
	start_date = forms.DateField(label="Data Hahu", widget=forms.DateInput(attrs={'type': 'date'}))
	end_date = forms.DateField(label="Data Remata", widget=forms.DateInput(attrs={'type': 'date'}))
	file = forms.FileField(label="Anexa (PDF, opsional)", required=False)

	def __init__(self, *args, employee=None, today=None, **kwargs):
		super().__init__(*args, **kwargs)
		self.employee = employee
		self.today = today or datetime.date.today()
		for f in self.fields.values():
			f.widget.attrs.setdefault('class', 'form-control')

	def clean_file(self):
		f = self.cleaned_data.get('file')
		if f:
			if not f.name.lower().endswith('.pdf'):
				raise forms.ValidationError("Ficheiru tenke PDF.")
			if f.size > MAX_FILE_BYTES:
				raise forms.ValidationError("Ficheiru boot liu 5 MB.")
			if f.read(5) != b'%PDF-':
				raise forms.ValidationError("Ficheiru la'ós PDF loos.")
			f.seek(0)
		return f

	def clean(self):
		data = super().clean()
		s, e = data.get('start_date'), data.get('end_date')
		if s and e:
			if e < s:
				raise forms.ValidationError("Data remata labele molok data hahu.")
			if (e - s).days + 1 > MAX_DAYS:
				raise forms.ValidationError("Lisensa labele liu %d loron." % MAX_DAYS)
			if s < self.today - datetime.timedelta(days=MAX_BACKDATE_DAYS):
				raise forms.ValidationError("Data hahu labele liu %d loron kotuk." % MAX_BACKDATE_DAYS)
			if self.employee and Leaves.objects.filter(
					employee=self.employee, is_active=True, start_date__lte=e, end_date__gte=s).exists():
				raise forms.ValidationError("Iha ona pedidu/lisensa seluk iha periodu ne'e.")
		return data
