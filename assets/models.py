from django.contrib.auth.models import User
from django.db import models

from employee.models import Employee

# status aset. 'in_use' = dipakai staf; 'in_stock' = stok di logistik (taruh di rak)
STATUSES = ('new', 'in_use', 'returned', 'in_repair', 'broken', 'in_stock')
# status di bawah ini berarti barang ada di tangan seorang staf; selain itu barang di logistik (holder kosong)
HELD_STATUSES = ('in_use', 'in_repair', 'broken')
EVENT_KINDS = ('create', 'assign', 'return', 'status', 'shelf', 'survey')


class AssetCategory(models.Model):
	"""Kategori aset. `code` dikenal (computer, laptop, ...) = namanya diterjemahkan otomatis; kategori buatan admin memakai `name`."""
	code = models.CharField(max_length=20, unique=True, null=True, blank=True)
	name = models.CharField(max_length=60, unique=True)

	class Meta:
		ordering = ['name']
		verbose_name_plural = 'asset categories'

	def __str__(self):
		return self.name


class Asset(models.Model):
	"""Satu barang inventaris. Pemegang saat ini = `holder`; riwayat lengkap di AssetEvent."""
	code = models.CharField(max_length=40, unique=True)                 # nomor inventaris / label yang ditempel di barang
	name = models.CharField(max_length=100)
	category = models.ForeignKey(AssetCategory, on_delete=models.PROTECT, related_name='assets')
	brand = models.CharField(max_length=60, blank=True)
	model = models.CharField(max_length=60, blank=True)
	serial_number = models.CharField(max_length=80, blank=True)
	purchase_date = models.DateField(null=True, blank=True)
	status = models.CharField(max_length=12, default='new', db_index=True)
	holder = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='assets')
	shelf = models.CharField(max_length=60, blank=True)                 # lokasi di logistik, mis. "Rak B-2"
	notes = models.CharField(max_length=300, blank=True)
	is_active = models.BooleanField(default=True)                       # False = dihapusbukukan (tidak dihitung lagi)
	last_checked = models.DateTimeField(null=True, blank=True)          # survei terakhir
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

	class Meta:
		ordering = ['code']
		indexes = [models.Index(fields=['status', 'is_active'])]

	def __str__(self):
		return '%s - %s' % (self.code, self.name)


class AssetEvent(models.Model):
	"""Riwayat: tidak pernah diubah atau dihapus oleh aplikasi (bukti audit)."""
	asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='events')
	kind = models.CharField(max_length=10)
	from_status = models.CharField(max_length=12, blank=True)
	to_status = models.CharField(max_length=12, blank=True)
	employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
	shelf = models.CharField(max_length=60, blank=True)
	note = models.CharField(max_length=300, blank=True)
	at = models.DateTimeField()
	user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

	class Meta:
		ordering = ['-at', '-id']
