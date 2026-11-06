from django import forms

from custom.models import DG, Department, Division, Position, Section
from main import ui


class PlacementForm(forms.Form):
	position = forms.ModelChoiceField(Position.objects.order_by('name'))
	dg = forms.ModelChoiceField(DG.objects.order_by('name'), required=False)
	division = forms.ModelChoiceField(Division.objects.order_by('name'), required=False)
	department = forms.ModelChoiceField(Department.objects.order_by('name'), required=False)
	section = forms.ModelChoiceField(Section.objects.order_by('name'), required=False)
	start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
	disp_number = forms.CharField(max_length=50, required=False)

	def __init__(self, *args, last_start=None, lang='tet', **kwargs):
		super().__init__(*args, **kwargs)
		self.last_start = last_start
		self.lang = lang
		ui.set_labels(self, lang, {'position': 'f.position', 'dg': 'f.dg', 'division': 'f.division',
			'department': 'f.department', 'section': 'f.section', 'start_date': 'f.start', 'disp_number': 'f.disp'})
		self.fields['position'].empty_label = ui.tr(lang, 'form.choose')
		for n in ('dg', 'division', 'department', 'section'):
			self.fields[n].empty_label = ui.tr(lang, 'form.blank')
		for f in self.fields.values():
			f.widget.attrs.setdefault('class', 'form-control')

	def _err(self, key, **kw):
		return forms.ValidationError(ui.tr(self.lang, key, **kw))

	def clean(self):
		d = super().clean()
		dg, div, dep, sec = d.get('dg'), d.get('division'), d.get('department'), d.get('section')
		if div and dg and div.dg_id != dg.pk:
			raise self._err('place.err.div_dg')
		if dep and div and dep.division_id != div.pk:
			raise self._err('place.err.dep_div')
		if sec and dep and sec.department_id != dep.pk:
			raise self._err('place.err.sec_dep')
		if (dep or sec) and not div:
			raise self._err('place.err.need_div')
		if div and not dg:
			d['dg'] = div.dg
		if self.last_start and d.get('start_date') and d['start_date'] < self.last_start:
			raise self._err('place.err.before', date=self.last_start.strftime('%d/%m/%Y'))
		return d
