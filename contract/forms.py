from django import forms

from custom.models import Division, Position
from main import ui


class PlacementForm(forms.Form):
	position = forms.ModelChoiceField(Position.objects.order_by('name'))
	division = forms.ModelChoiceField(Division.objects.order_by('name'), required=False)
	start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
	disp_number = forms.CharField(max_length=50, required=False)

	def __init__(self, *args, last_start=None, lang='tet', **kwargs):
		super().__init__(*args, **kwargs)
		self.last_start = last_start
		self.lang = lang
		ui.set_labels(self, lang, {'position': 'f.position', 'division': 'f.division', 'start_date': 'f.start', 'disp_number': 'f.disp'})
		self.fields['position'].empty_label = ui.tr(lang, 'form.choose')
		self.fields['division'].empty_label = ui.tr(lang, 'form.blank')
		for f in self.fields.values():
			f.widget.attrs.setdefault('class', 'form-control')
		ui.localize_errors(self, lang)

	def _err(self, key, **kw):
		return forms.ValidationError(ui.tr(self.lang, key, **kw))

	def clean(self):
		d = super().clean()
		if self.last_start and d.get('start_date') and d['start_date'] < self.last_start:
			raise self._err('place.err.before', date=self.last_start.strftime('%d/%m/%Y'))
		return d
