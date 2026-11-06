from django.db import models
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User
from employee.models import Employee
from settings_app.upload_utils import upload_leave

class LeaveType(models.Model):
	code = models.CharField(max_length=10, null=True, blank=True)
	name = models.CharField(max_length=100, null=True, blank=True)
	artigo = models.CharField(max_length=20, null=True, blank=True, verbose_name="Artigo")
	
	def __str__(self):
		template = '{0.code} -> {0.name}'
		return template.format(self)

class LeaveNotes(models.Model):
	name = models.CharField(max_length=200, null=True, blank=True)
	def __str__(self):
		template = '{0.name}'
		return template.format(self)

class Leaves(models.Model):
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leaves', verbose_name="Pessoal")
	leave_type = models.ForeignKey(LeaveType, null=True, on_delete=models.CASCADE, related_name='leaves', verbose_name="Tipu Licensa")
	start_date = models.DateField(null=False, verbose_name="Data Hahu")
	end_date = models.DateField(null=False, verbose_name="Data Remata")
	is_active = models.BooleanField(default=True, null=True)
	is_confirm = models.BooleanField(default=False, null=True)
	annualleave_conn = models.IntegerField(null=True, blank=True)
	start_datetime = models.DateTimeField(null=True, blank=True)
	end_datetime = models.DateTimeField(null=True, blank=True)
	file = models.FileField(upload_to=upload_leave, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexa Licenca")
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	hashed = models.CharField(max_length=32, null=True)

class LeavesFormat(models.Model):
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leavesformat', verbose_name="Pessoal")
	leaves = models.ForeignKey(Leaves, on_delete=models.CASCADE, related_name='leavesformat', verbose_name="Licenca")
	notes = models.ForeignKey(LeaveNotes, null=True, on_delete=models.CASCADE, related_name='leavesformat', verbose_name="Nota")
	to_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Diriji Ba")
	to_position = models.CharField(max_length=50, null=True, blank=True, verbose_name="Pojisaun")
	subject = models.CharField(max_length=200, null=True, blank=True, verbose_name="Assuntu")
	days = models.IntegerField(default=0, null=False, verbose_name="Total Loron")
	sup_one_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Naran")
	sup_one_position = models.CharField(max_length=100, null=True, blank=True, verbose_name="Pojisaun")
	sup_two_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Naran")
	sup_two_position = models.CharField(max_length=100, null=True, blank=True, verbose_name="Pojisaun")
	sup_three_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Naran")
	sup_three_position = models.CharField(max_length=100, null=True, blank=True, verbose_name="Pojisaun")
	def __str__(self):
		template = '{0.leaves}'
		return template.format(self)

class Year(models.Model):
	year = models.IntegerField(null=True, blank=True)
	is_active = models.BooleanField(default=False)
	def __str__(self):
		template = '{0.year}'
		return template.format(self)

class AnnualLeaves(models.Model):
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='annualleaves', verbose_name="Pessoal")
	leave_type = models.ForeignKey(LeaveType, null=True, on_delete=models.CASCADE, related_name='annualleaves', verbose_name="Tipu Licensa")
	year = models.ForeignKey(Year, on_delete=models.CASCADE, related_name='annualleaves', verbose_name="Tinan")
	start_date = models.DateField(null=True, blank=True, verbose_name="Data Hahu")
	end_date = models.DateField(null=True, blank=True, verbose_name="Data Remata")
	days = models.IntegerField(default=0, null=False, blank=True, verbose_name="Total Loron")
	remain = models.IntegerField(default=0, null=False, blank=True, verbose_name="Hela Loron")
	is_active = models.BooleanField(default=True, null=True)
	is_confirm = models.BooleanField(default=False, null=True)
	file = models.FileField(upload_to=upload_leave, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexa Licenca")
	start_datetime = models.DateTimeField(null=True, blank=True)
	end_datetime = models.DateTimeField(null=True, blank=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	hashed = models.CharField(max_length=32, null=True)
