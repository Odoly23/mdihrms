"""Aturan perpindahan status aset. Semua perubahan lewat sini (satu transaksi, baris dikunci) dan selalu mencatat AssetEvent."""
import datetime

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from .models import Asset, AssetCategory, AssetEvent, HELD_STATUSES, STATUSES

# status yang boleh dipilih pegawai untuk barang yang dipegangnya sendiri (survei mandiri)
SELF_STATUSES = ('in_use', 'broken')
# status awal yang boleh untuk barang yang diserahkan ke staf
ASSIGNABLE_FROM = ('new', 'in_stock', 'returned')
SURVEY_STALE_DAYS = 90


class AssetError(Exception):
	"""Aturan dilanggar; `key` = kunci terjemahan pesan, `params` = parameternya."""

	def __init__(self, key, **params):
		super().__init__(key)
		self.key, self.params = key, params


def _log(asset, kind, user, now, *, from_status='', to_status='', employee=None, shelf='', note=''):
	AssetEvent.objects.create(asset=asset, kind=kind, from_status=from_status, to_status=to_status, employee=employee,
		shelf=(shelf or '')[:60], note=(note or '')[:300], at=now, user=user)


def _lock(asset_id):
	return Asset.objects.select_for_update().get(pk=asset_id)


@transaction.atomic
def create(asset, user, now=None):
	"""Simpan aset baru (status 'new' atau 'in_stock' dengan rak); tidak boleh langsung dipegang orang."""
	now = now or timezone.now()
	if asset.status not in ('new', 'in_stock', 'returned', 'broken', 'in_repair'):
		raise AssetError('asset.err.status_new')
	asset.holder = None
	asset.user = user
	asset.save()
	_log(asset, 'create', user, now, to_status=asset.status, shelf=asset.shelf)
	return asset


@transaction.atomic
def assign(asset_id, employee, user, note='', now=None):
	"""Serahkan barang dari logistik ke staf: status 'in_use', rak dikosongkan."""
	now = now or timezone.now()
	a = _lock(asset_id)
	if not a.is_active:
		raise AssetError('asset.err.inactive')
	if a.holder_id or a.status not in ASSIGNABLE_FROM:
		raise AssetError('asset.err.not_available')
	old = a.status
	a.holder, a.status, a.shelf, a.last_checked = employee, 'in_use', '', now
	a.save()
	_log(a, 'assign', user, now, from_status=old, to_status='in_use', employee=employee, note=note)
	return a


@transaction.atomic
def return_asset(asset_id, user, to_status='returned', shelf='', note='', now=None):
	"""Staf mengembalikan barang ke logistik. Status 'returned' (menunggu dicek), 'broken', atau 'in_stock' (langsung ke rak)."""
	now = now or timezone.now()
	a = _lock(asset_id)
	if not a.holder_id:
		raise AssetError('asset.err.no_holder')
	if to_status not in ('returned', 'broken', 'in_stock', 'in_repair'):
		raise AssetError('asset.err.status_return')
	if to_status == 'in_stock' and not (shelf or '').strip():
		raise AssetError('asset.err.shelf_required')
	holder, old = a.holder, a.status
	a.holder, a.status, a.shelf, a.last_checked = None, to_status, (shelf or '').strip()[:60] if to_status == 'in_stock' else '', now
	a.save()
	_log(a, 'return', user, now, from_status=old, to_status=to_status, employee=holder, shelf=a.shelf, note=note)
	return a


@transaction.atomic
def set_status(asset_id, to_status, user, shelf='', note='', now=None, self_service_for=None):
	"""Ubah status (survei atau perbaikan). self_service_for = pegawai peminta: hanya barang miliknya dan hanya SELF_STATUSES."""
	now = now or timezone.now()
	a = _lock(asset_id)
	if to_status not in STATUSES:
		raise AssetError('asset.err.status_bad')
	if self_service_for is not None:
		if a.holder_id != self_service_for.pk:
			raise AssetError('asset.err.not_yours')
		if to_status not in SELF_STATUSES:
			raise AssetError('asset.err.status_self')
	if to_status == 'in_use' and not a.holder_id:
		raise AssetError('asset.err.use_needs_holder')            # pakai 'assign' untuk menyerahkan barang
	if to_status == 'in_stock' and not (shelf or '').strip():
		raise AssetError('asset.err.shelf_required')
	old, holder = a.status, a.holder
	a.status = to_status
	if to_status in ('new', 'returned', 'in_stock'):              # barang kembali di logistik: tidak ada pemegang
		a.holder = None
		a.shelf = (shelf or '').strip()[:60] if to_status == 'in_stock' else ''
	elif to_status in HELD_STATUSES and not a.holder_id:          # rusak/diperbaiki di logistik: tetap tanpa pemegang
		a.shelf = (shelf or '').strip()[:60] if shelf else a.shelf
	a.last_checked = now
	a.save()
	_log(a, 'status', user, now, from_status=old, to_status=to_status, employee=holder, shelf=a.shelf, note=note)
	return a


@transaction.atomic
def move_shelf(asset_id, shelf, user, note='', now=None):
	now = now or timezone.now()
	a = _lock(asset_id)
	if a.holder_id:
		raise AssetError('asset.err.held_shelf')
	shelf = (shelf or '').strip()[:60]
	if not shelf:
		raise AssetError('asset.err.shelf_required')
	a.shelf = shelf
	a.save()
	_log(a, 'shelf', user, now, shelf=shelf, note=note)
	return a


@transaction.atomic
def confirm(asset_id, user, note='', now=None, self_service_for=None):
	"""Survei: barang diperiksa dan statusnya tetap (hanya mengisi 'terakhir dicek')."""
	now = now or timezone.now()
	a = _lock(asset_id)
	if self_service_for is not None and a.holder_id != self_service_for.pk:
		raise AssetError('asset.err.not_yours')
	a.last_checked = now
	a.save(update_fields=['last_checked', 'updated_at'])
	_log(a, 'survey', user, now, from_status=a.status, to_status=a.status, employee=a.holder, shelf=a.shelf, note=note)
	return a


def summary(now=None):
	"""Tabel survei: {kategori: {status: jumlah}} untuk aset aktif, plus total per status, stok logistik (barang tanpa pemegang)
	dan yang perlu perhatian. Jumlah query tetap (5), berapa pun jumlah barangnya."""
	now = now or timezone.now()
	rows = (Asset.objects.filter(is_active=True).values('category_id', 'status').annotate(n=Count('id')))
	cats = list(AssetCategory.objects.order_by('name'))
	table = {c.pk: {'category': c, 'by': {s: 0 for s in STATUSES}, 'total': 0} for c in cats}
	totals = {s: 0 for s in STATUSES}
	for r in rows:
		t = table.get(r['category_id'])
		if t is None or r['status'] not in totals:
			continue
		t['by'][r['status']] += r['n']
		t['total'] += r['n']
		totals[r['status']] += r['n']
	stale_before = now - datetime.timedelta(days=SURVEY_STALE_DAYS)
	attention = (Asset.objects.filter(is_active=True, status__in=('broken', 'in_repair')).select_related('category', 'holder').order_by('status', 'code')[:50])
	stale = Asset.objects.filter(is_active=True).exclude(status__in=('broken', 'in_repair')).filter(
		models_q_stale(stale_before)).count()
	return {'rows': [table[c.pk] for c in cats if table[c.pk]['total']], 'totals': totals, 'grand': sum(totals.values()),
		'stock': Asset.objects.filter(is_active=True, holder__isnull=True).count(), 'attention': attention, 'stale': stale,
		'stale_days': SURVEY_STALE_DAYS}


def models_q_stale(before):
	from django.db.models import Q
	return Q(last_checked__isnull=True) | Q(last_checked__lt=before)
