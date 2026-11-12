import datetime
from decimal import Decimal

from django import forms

from leave.models import Leaves
from main import ui

from .models import ALLOWED_EXT, HealthClaim
from .services import MAX_AGE_DAYS, MAX_AMOUNT

MAX_FILE = 5 * 1024 * 1024
_MAGIC = {'pdf': (b'%PDF-',), 'png': (b'\x89PNG\r\n\x1a\n',), 'jpg': (b'\xff\xd8\xff',), 'jpeg': (b'\xff\xd8\xff',)}


class ClaimForm(forms.ModelForm):
	class Meta:
		model = HealthClaim
		fields = ['claim_date', 'leave', 'description', 'amount', 'receipt']

	def __init__(self, *args, employee=None, lang='tet', today=None, **kwargs):
		super().__init__(*args, **kwargs)
		self.employee, self.lang = employee, lang
		self.today = today or datetime.date.today()
		ui.set_labels(self, lang, {'claim_date': 'hl.f.date', 'leave': 'hl.f.leave', 'description': 'hl.f.desc', 'amount': 'hl.f.amount',
			'receipt': 'hl.f.receipt'})
		self.fields['claim_date'].widget = forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
		self.fields['leave'].required = False
		self.fields['leave'].empty_label = ui.tr(lang, 'form.blank')
		self.fields['leave'].queryset = (Leaves.objects.filter(employee=employee, is_active=True, is_confirm=True).order_by('-start_date')
			if employee else Leaves.objects.none())
		self.fields['leave'].label_from_instance = lambda lv: '%s – %s' % (lv.start_date.strftime('%d/%m/%Y'), lv.end_date.strftime('%d/%m/%Y'))
		self.fields['amount'].widget = forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'inputmode': 'decimal'})
		self.fields['description'].widget.attrs['placeholder'] = ui.tr(lang, 'hl.desc_hint')
		for f in self.fields.values():
			f.widget.attrs.setdefault('class', 'form-control-file' if isinstance(f.widget, forms.ClearableFileInput) else 'form-control')
		ui.localize_errors(self, lang)

	def _err(self, key, **kw):
		return forms.ValidationError(ui.tr(self.lang, key, **kw))

	def clean_claim_date(self):
		d = self.cleaned_data['claim_date']
		if d > self.today:
			raise self._err('hl.err.date_future')
		if d < self.today - datetime.timedelta(days=MAX_AGE_DAYS):
			raise self._err('hl.err.date_old', n=MAX_AGE_DAYS)
		return d

	def clean_amount(self):
		a = self.cleaned_data['amount']
		if a is None or a <= Decimal('0'):
			raise self._err('hl.err.amount')
		if a > MAX_AMOUNT:
			raise self._err('hl.err.amount_max', n=MAX_AMOUNT)
		return a.quantize(Decimal('0.01'))

	def clean_receipt(self):
		f = self.cleaned_data.get('receipt')
		if not f:
			raise self._err('err.required')
		ext = f.name.rsplit('.', 1)[-1].lower() if '.' in f.name else ''
		if ext not in ALLOWED_EXT:
			raise self._err('hl.err.file_type')
		if f.size > MAX_FILE:
			raise self._err('hl.err.file_size')
		head = f.read(8)
		f.seek(0)
		if not any(head.startswith(m) for m in _MAGIC[ext]):
			raise self._err('hl.err.file_invalid')
		return f

	def clean(self):
		data = super().clean()
		d, a = data.get('claim_date'), data.get('amount')
		if self.employee and d and a and HealthClaim.objects.filter(employee=self.employee, claim_date=d, amount=a,
				status__in=('pending', 'approved', 'paid')).exists():
			raise self._err('hl.err.dup')
		return data
