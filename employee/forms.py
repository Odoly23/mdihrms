import datetime
import re

from django import forms
from django.core.validators import validate_email

from custom.models import (AdministrativePost, Country, DG, Department, Division, Municipality, Position, Section,
	Status, Village)

from .models import Employee, IDFNumber

MAX_PHOTO_BYTES = 2 * 1024 * 1024
_PHONE_RE = re.compile(r'^[0-9+\-\s()]{6,20}$')


class DateInput(forms.DateInput):
	input_type = 'date'

	def __init__(self, **kw):
		kw.setdefault('format', '%Y-%m-%d')
		super().__init__(**kw)


def _style(form):
	for f in form.fields.values():
		w = f.widget
		if isinstance(w, forms.CheckboxInput):
			w.attrs.setdefault('class', 'form-check-input')
		elif isinstance(w, forms.ClearableFileInput):
			w.attrs.setdefault('class', 'form-control-file')
		else:
			w.attrs.setdefault('class', 'form-control')


class EmployeeForm(forms.ModelForm):
	"""Data pokok funsionariu + NRF, posisi/diresaun, kontak, foto. Disimpan oleh `EmployeeForm.save_all`."""
	date_of_birth = forms.DateField(label="Data Moris", widget=DateInput())
	nrf = forms.CharField(label="Nu. PMIS/NRF", max_length=30, required=False)
	position = forms.ModelChoiceField(Position.objects.order_by('name'), label="Pojisaun", required=False, empty_label="--")
	dg = forms.ModelChoiceField(DG.objects.order_by('name'), label="Diresaun Geral", required=False, empty_label="--")
	division = forms.ModelChoiceField(Division.objects.order_by('name'), label="Diresaun", required=False, empty_label="--")
	department = forms.ModelChoiceField(Department.objects.order_by('name'), label="Departamento", required=False, empty_label="--")
	section = forms.ModelChoiceField(Section.objects.order_by('name'), label="Seksaun", required=False, empty_label="--")
	phone = forms.CharField(label="Nu. Telemovel", max_length=20, required=False)
	email = forms.CharField(label="Email", max_length=50, required=False)
	image = forms.ImageField(label="Foto (JPG/PNG, max 2 MB)", required=False)
	create_account = forms.BooleanField(label="Halo konta login", required=False, initial=True)

	class Meta:
		model = Employee
		fields = ['first_name', 'last_name', 'place_of_birth', 'date_of_birth', 'sex', 'marital', 'ran', 'country',
			'father', 'mother', 'status']

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['first_name'].required = True
		self.fields['country'].queryset = Country.objects.order_by('name')
		self.fields['country'].required = False
		self.fields['status'].queryset = Status.objects.order_by('id')
		self.fields['status'].required = True
		if not self.instance.pk:
			self.fields['status'].initial = 1
		else:
			self.fields.pop('create_account')
			self._load_related()
		_style(self)

	def _load_related(self):
		e = self.instance
		idf = IDFNumber.objects.filter(employee=e).first()
		self.initial['nrf'] = idf.nrf if idf else ''
		pos = getattr(e, 'employeeposition', None) if hasattr(e, 'employeeposition') else None
		div = getattr(e, 'employeedivision', None) if hasattr(e, 'employeedivision') else None
		contact = getattr(e, 'contactinfo', None) if hasattr(e, 'contactinfo') else None
		if pos:
			self.initial['position'] = pos.position_id
		if div:
			self.initial.update(dg=div.dg_id, division=div.division_id, department=div.department_id, section=div.section_id)
		if contact:
			self.initial.update(phone=contact.phone, email=contact.email)

	def clean_date_of_birth(self):
		d = self.cleaned_data['date_of_birth']
		today = datetime.date.today()
		if d >= today or (today.year - d.year) > 100:
			raise forms.ValidationError("Data moris la loos.")
		return d

	def clean_nrf(self):
		nrf = (self.cleaned_data.get('nrf') or '').strip()
		if nrf:
			qs = IDFNumber.objects.filter(nrf__iexact=nrf)
			if self.instance.pk:
				qs = qs.exclude(employee=self.instance)
			if qs.exists():
				raise forms.ValidationError("NRF ne'e uza ona.")
		return nrf

	def clean_phone(self):
		v = (self.cleaned_data.get('phone') or '').strip()
		if v and not _PHONE_RE.match(v):
			raise forms.ValidationError("Nu. telemovel la loos.")
		return v

	def clean_email(self):
		v = (self.cleaned_data.get('email') or '').strip()
		if v:
			validate_email(v)
		return v

	def clean_image(self):
		f = self.cleaned_data.get('image')
		if f and hasattr(f, 'size') and f.size > MAX_PHOTO_BYTES:
			raise forms.ValidationError("Foto boot liu 2 MB.")
		return f

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
		return d


class AddressForm(forms.Form):
	"""Hela fatin iha Timor-Leste (LocationTL): municipiu → posto → suco, dropdown berantai."""
	municipality = forms.ModelChoiceField(Municipality.objects.order_by('name'), label="Municipiu", required=False, empty_label="--")
	administrativepost = forms.ModelChoiceField(AdministrativePost.objects.none(), label="Posto", required=False, empty_label="--")
	village = forms.ModelChoiceField(Village.objects.none(), label="Suco", required=False, empty_label="--")
	aldeia = forms.CharField(label="Aldeia", max_length=50, required=False)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		src = self.data if self.is_bound else self.initial

		def num(key):
			try:
				return int(src.get(key))
			except (TypeError, ValueError):
				return None
		m, p = num('municipality'), num('administrativepost')
		if m:
			self.fields['administrativepost'].queryset = AdministrativePost.objects.filter(municipality_id=m).order_by('name')
		if p:
			self.fields['village'].queryset = Village.objects.filter(administrativepost_id=p).order_by('name')
		_style(self)

	def clean(self):
		d = super().clean()
		m, p, v = d.get('municipality'), d.get('administrativepost'), d.get('village')
		if p and (not m or p.municipality_id != m.pk):
			raise forms.ValidationError("Posto la tama iha Municipiu ne'ebé hili.")
		if v and (not p or v.administrativepost_id != p.pk):
			raise forms.ValidationError("Suco la tama iha Posto ne'ebé hili.")
		return d
