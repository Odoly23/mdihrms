import datetime

from django import forms

from employee.models import Employee
from main import ui

from .models import Asset, AssetCategory, STATUSES

_CSS = {'class': 'form-control'}


def _style(form):
	for f in form.fields.values():
		f.widget.attrs.setdefault('class', 'form-check-input' if isinstance(f.widget, forms.CheckboxInput) else 'form-control')


def category_name(cat, lang):
	"""Nama kategori bawaan (code dikenal) diterjemahkan; kategori buatan admin apa adanya."""
	if cat.code:
		key = 'cat.' + cat.code
		from attendance import qr_i18n
		if key in qr_i18n.MESSAGES:
			return qr_i18n.tr(lang, key)
	return cat.name


class AssetForm(forms.ModelForm):
	"""Tambah/ubah data barang. Status awal hanya 'baru' atau 'stok (di rak)'; perubahan status selanjutnya lewat tindakan terpisah."""
	status = forms.ChoiceField(choices=[], required=False)

	class Meta:
		model = Asset
		fields = ['code', 'name', 'category', 'brand', 'model', 'serial_number', 'purchase_date', 'status', 'shelf', 'notes']

	def __init__(self, *args, lang='tet', **kwargs):
		super().__init__(*args, **kwargs)
		self.lang = lang
		ui.set_labels(self, lang, {'code': 'as.f.code', 'name': 'th.name', 'category': 'as.f.category', 'brand': 'as.f.brand',
			'model': 'as.f.model', 'serial_number': 'as.f.serial', 'purchase_date': 'as.f.purchase', 'status': 'th.status',
			'shelf': 'as.f.shelf', 'notes': 'as.f.notes'})
		self.fields['category'].queryset = AssetCategory.objects.order_by('name')
		self.fields['category'].label_from_instance = lambda c: category_name(c, lang)
		self.fields['category'].empty_label = ui.tr(lang, 'form.choose')
		self.fields['purchase_date'].widget = forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
		if self.instance.pk:                                   # ubah data: status dan rak tidak diedit di sini
			self.fields.pop('status')
			self.fields.pop('shelf')
		else:
			self.fields['status'].choices = [('new', ui.tr(lang, 'ast.new')), ('in_stock', ui.tr(lang, 'ast.in_stock'))]
			self.fields['status'].initial = 'new'
		_style(self)
		ui.localize_errors(self, lang)

	def clean_code(self):
		code = ' '.join((self.cleaned_data.get('code') or '').split())
		qs = Asset.objects.filter(code__iexact=code)
		if self.instance.pk:
			qs = qs.exclude(pk=self.instance.pk)
		if qs.exists():
			raise forms.ValidationError(ui.tr(self.lang, 'as.err.code_dup'))
		return code

	def clean_purchase_date(self):
		d = self.cleaned_data.get('purchase_date')
		if d and (d > datetime.date.today() or d.year < 1990):
			raise forms.ValidationError(ui.tr(self.lang, 'as.err.date'))
		return d

	def clean(self):
		data = super().clean()
		if 'status' in self.fields and data.get('status') == 'in_stock' and not (data.get('shelf') or '').strip():
			self.add_error('shelf', ui.tr(self.lang, 'asset.err.shelf_required'))
		if 'status' in self.fields and data.get('status') == 'new':
			data['shelf'] = (data.get('shelf') or '').strip()
		return data


class AssignForm(forms.Form):
	employee = forms.ModelChoiceField(Employee.objects.none())
	note = forms.CharField(max_length=300, required=False)

	def __init__(self, *args, lang='tet', **kwargs):
		super().__init__(*args, **kwargs)
		ui.set_labels(self, lang, {'employee': 'th.emp', 'note': 'th.note'})
		self.fields['employee'].queryset = Employee.objects.filter(status_id=1).order_by('first_name', 'last_name')
		self.fields['employee'].empty_label = ui.tr(lang, 'form.choose')
		_style(self)
		ui.localize_errors(self, lang)


class ReturnForm(forms.Form):
	to_status = forms.ChoiceField(choices=[])
	shelf = forms.CharField(max_length=60, required=False)
	note = forms.CharField(max_length=300, required=False)

	def __init__(self, *args, lang='tet', **kwargs):
		super().__init__(*args, **kwargs)
		ui.set_labels(self, lang, {'to_status': 'th.status', 'shelf': 'as.f.shelf', 'note': 'th.note'})
		self.fields['to_status'].choices = [(s, ui.tr(lang, 'ast.' + s)) for s in ('returned', 'in_stock', 'broken', 'in_repair')]
		_style(self)
		ui.localize_errors(self, lang)


class StatusForm(forms.Form):
	to_status = forms.ChoiceField(choices=[])
	shelf = forms.CharField(max_length=60, required=False)
	note = forms.CharField(max_length=300, required=False)

	def __init__(self, *args, lang='tet', **kwargs):
		super().__init__(*args, **kwargs)
		ui.set_labels(self, lang, {'to_status': 'th.status', 'shelf': 'as.f.shelf', 'note': 'th.note'})
		self.fields['to_status'].choices = [(s, ui.tr(lang, 'ast.' + s)) for s in STATUSES if s != 'in_use']
		_style(self)
		ui.localize_errors(self, lang)
