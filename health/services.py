"""Aturan klaim health care: batas tahunan (opsional), tidak boleh menyetujui klaim sendiri, tidak ada keputusan ganda."""
import datetime
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import HealthClaim

MAX_AGE_DAYS = 90
DEFAULT_BONUS = Decimal('50.00')


class ClaimError(Exception):
	def __init__(self, key, **params):
		super().__init__(key)
		self.key, self.params = key, params


def bonus_amount():
	"""Bonus health care tetap per sakit (US$). Setelan: MDI_HEALTH_BONUS (bawaan 50)."""
	v = getattr(settings, 'MDI_HEALTH_BONUS', None)
	try:
		amount = Decimal(str(v)) if v not in (None, '') else DEFAULT_BONUS
	except Exception:
		return DEFAULT_BONUS
	return amount.quantize(Decimal('0.01')) if amount > 0 else DEFAULT_BONUS


def annual_limit():
	"""Batas persetujuan per pegawai per tahun kalender (US$), atau None bila tidak dibatasi. Setelan: MDI_HEALTH_ANNUAL_LIMIT."""
	v = getattr(settings, 'MDI_HEALTH_ANNUAL_LIMIT', None)
	return Decimal(str(v)) if v not in (None, '') else None


def used_in_year(employee, year, exclude_pk=None):
	qs = HealthClaim.objects.filter(employee=employee, status__in=('approved', 'paid'), claim_date__year=year)
	if exclude_pk:
		qs = qs.exclude(pk=exclude_pk)
	return qs.aggregate(t=Sum('approved_amount'))['t'] or Decimal('0')


def year_summary(employee, year):
	limit, used = annual_limit(), used_in_year(employee, year)
	return {'year': year, 'used': used, 'limit': limit, 'left': (limit - used) if limit is not None else None}


@transaction.atomic
def decide(claim_id, approve, user, note='', approver_employee=None, now=None):
	"""Setujui (bonus tetap sebesar jumlah klaim, dan tidak melewati sisa batas tahunan bila ada) atau tolak. Baris dikunci; hanya 'pending'."""
	now = now or timezone.now()
	c = HealthClaim.objects.select_for_update().select_related('employee').get(pk=claim_id)
	if approver_employee is not None and c.employee_id == approver_employee.pk:
		raise ClaimError('hl.err.own')
	if c.status != 'pending':
		raise ClaimError('hl.err.done')
	if approve:
		amount = c.amount                                   # bonus tetap: tidak ada persetujuan sebagian
		limit = annual_limit()
		if limit is not None:
			left = limit - used_in_year(c.employee, c.claim_date.year, exclude_pk=c.pk)
			if amount > left:
				raise ClaimError('hl.err.over_cap', left='%.2f' % max(left, Decimal('0')))
		c.status, c.approved_amount = 'approved', amount
	else:
		c.status, c.approved_amount = 'rejected', None
	c.decided_by, c.decided_at, c.decision_note = user, now, (note or '')[:200]
	c.save()
	return c


@transaction.atomic
def mark_paid(claim_id, user, now=None):
	now = now or timezone.now()
	c = HealthClaim.objects.select_for_update().get(pk=claim_id)
	if c.status != 'approved':
		raise ClaimError('hl.err.not_approved')
	c.status, c.paid_at = 'paid', now
	c.save(update_fields=['status', 'paid_at'])
	return c


@transaction.atomic
def cancel(claim_id, employee):
	c = HealthClaim.objects.select_for_update().get(pk=claim_id, employee=employee)
	if c.status != 'pending':
		raise ClaimError('hl.err.done')
	c.delete()


def pending_count(exclude_employee_id=None):
	qs = HealthClaim.objects.filter(status='pending')
	if exclude_employee_id:
		qs = qs.exclude(employee_id=exclude_employee_id)
	return qs.count()
