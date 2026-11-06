from django import forms

from custom.models import DG, Department, Division, Position, Section


class PlacementForm(forms.Form):
	position = forms.ModelChoiceField(Position.objects.order_by('name'), label="Pojisaun", empty_label="-- Hili --")
	dg = forms.ModelChoiceField(DG.objects.order_by('name'), label="Diresaun Geral", required=False, empty_label="--")
	division = forms.ModelChoiceField(Division.objects.order_by('name'), label="Diresaun", required=False, empty_label="--")
	department = forms.ModelChoiceField(Department.objects.order_by('name'), label="Departamento", required=False, empty_label="--")
	section = forms.ModelChoiceField(Section.objects.order_by('name'), label="Seksaun", required=False, empty_label="--")
	start_date = forms.DateField(label="Data Hahu", widget=forms.DateInput(attrs={'type': 'date'}))
	disp_number = forms.CharField(label="Numeru Despacho", max_length=50, required=False)

	def __init__(self, *args, last_start=None, **kwargs):
		super().__init__(*args, **kwargs)
		self.last_start = last_start
		for f in self.fields.values():
			f.widget.attrs.setdefault('class', 'form-control')

	def clean(self):
		d = super().clean()
		dg, div, dep, sec = d.get('dg'), d.get('division'), d.get('department'), d.get('section')
		if div and dg and div.dg_id != dg.pk:
			raise forms.ValidationError("Diresaun la tama iha Diresaun Geral ne'ebé hili.")
		if dep and div and dep.division_id != div.pk:
			raise forms.ValidationError("Departamento la tama iha Diresaun ne'ebé hili.")
		if sec and dep and sec.department_id != dep.pk:
			raise forms.ValidationError("Seksaun la tama iha Departamento ne'ebé hili.")
		if (dep or sec) and not div:
			raise forms.ValidationError("Hili Diresaun molok Departamento/Seksaun.")
		if div and not dg:
			d['dg'] = div.dg
		if self.last_start and d.get('start_date') and d['start_date'] < self.last_start:
			raise forms.ValidationError("Data hahu labele molok kolokasaun ikus (%s)." % self.last_start.strftime('%d/%m/%Y'))
		return d
