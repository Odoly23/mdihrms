import os
import uuid

from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import models

from custom.models import Institute
from employee.models import Employee

# alur surat masuk: registered -> (returned -> registered) -> approved -> disposed -> done
STATUSES = ('registered', 'returned', 'approved', 'disposed', 'done')
ACTIONS = ('register', 'edit', 'approve', 'return', 'dispose', 'redispose', 'done')


def upload_letter(instance, filename):
	"""PDF surat disimpan dengan nama acak; diunduh lewat view yang memeriksa hak akses (tidak ada URL publik)."""
	return 'kts/%s/%s.pdf' % (instance.__class__.__name__.lower(), uuid.uuid4().hex)


class Tama(models.Model):
	"""Surat masuk (Karta Tama). Hanya resepsionis yang mendaftarkan; admin memverifikasi dan menyetujui; direktur mendisposisi ke
	penanggung jawab dengan despacho; penanggung jawab menyelesaikannya."""
	nu_ref = models.CharField(max_length=50, null=True, verbose_name="Numeru Referensia")
	institutu = models.ForeignKey(Institute, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Instituisaun")
	de = models.CharField(max_length=200, null=True, verbose_name="DE")
	para = models.CharField(max_length=200, null=True, verbose_name="Para")
	asuntu = models.CharField(max_length=200, null=True, verbose_name="Asuntu")
	data_kartatama = models.DateField(null=True, verbose_name="Data Karta Tama")
	entrega = models.CharField(max_length=100, null=True, blank=True, verbose_name="Entrega")
	obs = models.CharField(max_length=200, null=True, blank=True, verbose_name="Observasaun")
	file_pdf = models.FileField(upload_to=upload_letter, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexa Dokumentu / Karta")
	hashed = models.CharField(max_length=32, null=True)
	anu_letivu = models.CharField(max_length=4, null=True, verbose_name="Anu Letivu")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)       # pendaftar (CASCADE di versi lama berbahaya)
	# --- alur kerja
	status = models.CharField(max_length=10, default='registered', db_index=True)
	verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
	verified_at = models.DateTimeField(null=True, blank=True)
	verify_note = models.CharField(max_length=300, blank=True)
	disposed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
	disposed_at = models.DateTimeField(null=True, blank=True)
	despacho = models.TextField(blank=True)                                                 # instruksi direktur
	handler = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='kts_handled')
	due_date = models.DateField(null=True, blank=True)
	done_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
	done_at = models.DateTimeField(null=True, blank=True)
	done_note = models.CharField(max_length=500, blank=True)
	done_file = models.FileField(upload_to=upload_letter, null=True, blank=True, validators=[FileExtensionValidator(allowed_extensions=['pdf'])])

	class Meta:
		ordering = ['-data_kartatama', '-id']
		indexes = [models.Index(fields=['status', 'data_kartatama'])]

	def __str__(self):
		return '%s %s' % (self.nu_ref, self.asuntu)


class TamaEvent(models.Model):
	"""Riwayat surat masuk (bukti audit; tidak diubah oleh aplikasi)."""
	letter = models.ForeignKey(Tama, on_delete=models.CASCADE, related_name='events')
	action = models.CharField(max_length=10)
	from_status = models.CharField(max_length=10, blank=True)
	to_status = models.CharField(max_length=10, blank=True)
	user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
	employee = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')   # mis. penanggung jawab baru
	note = models.CharField(max_length=500, blank=True)
	at = models.DateTimeField()

	class Meta:
		ordering = ['-at', '-id']


class Sai(models.Model):
	"""Surat keluar (Karta Sai)."""
	nu_ref = models.CharField(max_length=50, null=True, verbose_name="Numeru Referensia")
	institutus = models.ForeignKey(Institute, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Instituisaun")
	de = models.CharField(max_length=200, null=True, verbose_name="DE")
	asuntu = models.CharField(max_length=200, null=True, verbose_name="Asuntu")
	para = models.CharField(max_length=100, null=True, verbose_name="Para")
	data_kartasai = models.DateField(null=True, verbose_name="Data Karta Sai")
	obs = models.CharField(max_length=200, null=True, blank=True, verbose_name="Observasaun")
	file_pdf = models.FileField(upload_to=upload_letter, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Dokumentu / Karta")
	hashed = models.CharField(max_length=32, null=True)
	anu_letivu = models.CharField(max_length=4, null=True, verbose_name="Anu Letivu")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)        # pembuat
	# --- alur: registered -> verified (administrasi) -> approved (direktur); returned bila perlu diperbaiki
	status = models.CharField(max_length=10, default='registered', db_index=True)
	verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
	verified_at = models.DateTimeField(null=True, blank=True)
	verify_note = models.CharField(max_length=300, blank=True)
	approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
	approved_at = models.DateTimeField(null=True, blank=True)
	approve_note = models.CharField(max_length=300, blank=True)

	class Meta:
		ordering = ['-data_kartasai', '-id']

	def __str__(self):
		return '%s %s' % (self.nu_ref, self.asuntu)


SAI_STATUSES = ('registered', 'returned', 'verified', 'approved')


class SaiEvent(models.Model):
	"""Riwayat surat keluar (bukti audit; tidak diubah oleh aplikasi)."""
	letter = models.ForeignKey(Sai, on_delete=models.CASCADE, related_name='events')
	action = models.CharField(max_length=10)
	from_status = models.CharField(max_length=10, blank=True)
	to_status = models.CharField(max_length=10, blank=True)
	user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
	note = models.CharField(max_length=500, blank=True)
	at = models.DateTimeField()

	class Meta:
		ordering = ['-at', '-id']
