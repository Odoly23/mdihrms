import os
import uuid

from django.contrib.auth.models import User
from django.db import models

from employee.models import Employee
from leave.models import Leaves

STATUSES = ('pending', 'approved', 'rejected', 'paid')
ALLOWED_EXT = ('pdf', 'jpg', 'jpeg', 'png')


def upload_receipt(instance, filename):
	"""Nama berkas diacak (tidak bisa ditebak) dan hanya ekstensi yang diizinkan; diunduh lewat view yang memeriksa hak akses."""
	ext = os.path.splitext(filename)[1].lower().lstrip('.')
	ext = ext if ext in ALLOWED_EXT else 'bin'
	return 'health_receipts/%s/%s.%s' % (instance.employee_id, uuid.uuid4().hex, ext)


class HealthClaim(models.Model):
	"""Klaim health care (bonus/penggantian biaya) staf yang sakit. Sengaja TIDAK menyimpan diagnosis: hanya tanggal, jumlah, dan bukti."""
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='healthclaims')
	claim_date = models.DateField()                                         # tanggal sakit/berobat
	leave = models.ForeignKey(Leaves, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')   # cuti sakit terkait (opsional)
	description = models.CharField(max_length=200, blank=True)             # keterangan singkat, bukan diagnosis
	amount = models.DecimalField(max_digits=10, decimal_places=2)          # jumlah yang diajukan (US$)
	receipt = models.FileField(upload_to=upload_receipt)
	status = models.CharField(max_length=10, default='pending', db_index=True)
	approved_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	decided_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
	decided_at = models.DateTimeField(null=True, blank=True)
	decision_note = models.CharField(max_length=200, blank=True)
	paid_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

	class Meta:
		ordering = ['-claim_date', '-id']
		indexes = [models.Index(fields=['status', 'claim_date'])]

	def __str__(self):
		return '%s %s US$%s' % (self.employee, self.claim_date, self.amount)
