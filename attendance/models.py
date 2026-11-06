# from pytz import timezone
import datetime
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from custom.models import DG, Division
from employee.models import Employee
from settings_app.upload_utils import upload_attendace, upload_leave

class AttendanceStatus(models.Model):
	code = models.CharField(max_length=10, null=True, blank=True)
	name = models.CharField(max_length=100, null=True, blank=True)
	def __str__(self):
		template = '{0.code} -> {0.name}'
		return template.format(self)

class Attendance(models.Model):
	dg = models.ForeignKey(DG, null=True, on_delete=models.CASCADE, related_name='attendance', verbose_name="Diresaun Geral")
	div = models.ForeignKey(Division, null=True, on_delete=models.CASCADE, related_name='attendance', verbose_name="Diresaun")
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance', verbose_name="Pessoal")
	status_am = models.ForeignKey(AttendanceStatus, null=True, on_delete=models.CASCADE, related_name='attendance_am', verbose_name="Dader")
	status_pm = models.ForeignKey(AttendanceStatus, null=True, on_delete=models.CASCADE, related_name='attendance_pm', verbose_name="Loro-Kraik")
	date = models.DateField(null=False, verbose_name="Data")
	desc = models.CharField(max_length=200, null=True, blank=True, verbose_name="Deskrisaun")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	hashed = models.CharField(max_length=32, null=True)

	def __str__(self):
		template = '{0.employee} {0.date}'
		return template.format(self)

class AttendanceDiv(models.Model):
	dg = models.ForeignKey(DG, null=True, on_delete=models.CASCADE, related_name='attendancediv', verbose_name="Diresaun")
	div = models.ForeignKey(Division, null=True, on_delete=models.CASCADE, related_name='attendancediv', verbose_name="Diresaun")
	year = models.IntegerField(null=True)
	month = models.IntegerField(null=True)
	is_confirm = models.BooleanField(default=False, null=True)
	is_final = models.BooleanField(default=False, null=True)
	file = models.FileField(upload_to=upload_attendace, null=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Upload PDF")
	
class Leave(models.Model):
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave', verbose_name="Pessoal")
	status = models.ForeignKey(AttendanceStatus, null=True, on_delete=models.CASCADE, related_name='leave', verbose_name="Tipu Licensa")
	to_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Ba")
	to_position = models.CharField(max_length=50, null=True, blank=True, verbose_name="Pojisaun")
	subject = models.CharField(max_length=200, null=True, blank=True, verbose_name="Assuntu")
	artigo = models.CharField(max_length=20, null=True, blank=True, verbose_name="Artigo")
	start_date = models.DateField(null=False, verbose_name="Data Hahu")
	end_date = models.DateField(null=False, verbose_name="Data Remata")
	days = models.IntegerField(default=0, null=False, verbose_name="Total Loron")
	sup_one_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Naran")
	sup_one_position = models.CharField(max_length=100, null=True, blank=True, verbose_name="Pojisaun")
	# sup_one_date = models.DateTimeField(null=True, blank=True)
	sup_two_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Naran")
	sup_two_position = models.CharField(max_length=100, null=True, blank=True, verbose_name="Pojisaun")
	# sup_two_date = models.DateTimeField(null=True, blank=True)
	sup_three_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Naran")
	sup_three_position = models.CharField(max_length=100, null=True, blank=True, verbose_name="Pojisaun")
	# sup_three_date = models.DateTimeField(null=True, blank=True)
	is_active = models.BooleanField(default=True, null=True)
	is_confirm = models.BooleanField(default=False, null=True)
	start_datetime = models.DateTimeField(null=True, blank=True)
	end_datetime = models.DateTimeField(null=True, blank=True)
	file = models.FileField(upload_to=upload_leave, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexa Licenca")
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	hashed = models.CharField(max_length=32, null=True)

	def __str__(self):
		template = '{0.leave_type}'
		return template.format(self)

class OverTime(models.Model):
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='overtime', verbose_name="Pessoal")
	date = models.DateField(null=False, blank=True, verbose_name="Data")
	start_time = models.TimeField(null=False, blank=True, verbose_name="Horas Hahu")
	end_time = models.TimeField(null=False, blank=True, verbose_name="Horas Remata")
	datetime = models.DateTimeField(null=True)
	is_active = models.BooleanField(default=True, null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	hashed = models.CharField(max_length=32, null=True)
	def __str__(self):
		template = '{0.leave_type}'
		return template.format(self)

class Year(models.Model):
	year = models.IntegerField(null=True, blank=True)
	is_active = models.BooleanField(default=False)
	def __str__(self):
		template = '{0.year}'
		return template.format(self)

class Month(models.Model):
	code = models.IntegerField(null=True, blank=True)
	name = models.CharField(max_length=20, null=True, blank=True)
	is_active = models.BooleanField(default=False)
	def __str__(self):
		template = '{0.name} '
		return template.format(self)

class NacionalHoliday(models.Model):
	name = models.CharField(max_length=100, null=True, blank=True)
	date = models.DateField(null=False)
	is_active = models.BooleanField(default=True, null=True)
	def __str__(self):
		template = '{0.date}'
		return template.format(self)

class Tolerance(models.Model):
	year = models.ForeignKey(Year, on_delete=models.CASCADE, related_name='holiday', verbose_name="Tinan")
	name = models.CharField(max_length=100, null=True, blank=True)
	date = models.DateField(null=False)
	is_active = models.BooleanField(default=True, null=True)
	def __str__(self):
		template = '{0.date}'
		return template.format(self)

# Absensi QR (kartu, kiosk, scan, log)
from attendance.models_qr import QRCard, ScanDevice, AttendanceTime, ScanLog, OfficeNetwork  # noqa: E402,F401
