from django.db import models
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User
from custom.models import Gabinete, Institute, DG, Division, Department, Position, Section,\
	ContractType, Category, Grade, Echelon, Status
from employee.models import Employee
from settings_app.upload_utils import upload_initial_contract, upload_contract, upload_koloka

class InitialContract(models.Model):
	pmis_id = models.CharField(max_length=20, null=True, blank=True, verbose_name="Nu. PMIS")
	employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="initialcontract", verbose_name="Pessoal")
	institute = models.ForeignKey(Institute, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Instituisaun")
	dg = models.ForeignKey(DG, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Diresaun Geral")
	division = models.ForeignKey(Division, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Diresaun")
	department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Departamento")
	section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Seksaun")
	contract_type = models.ForeignKey(ContractType, on_delete=models.CASCADE, null=True, blank=False, related_name="initialcontract", verbose_name="Tipu Kontratu")
	category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name="initialcontract", verbose_name="Kategoria")
	grade = models.ForeignKey(Grade, on_delete=models.CASCADE, null=True, blank=True, related_name="initialcontract", verbose_name="Grau")
	echelon = models.ForeignKey(Echelon, on_delete=models.CASCADE, null=True, blank=True, related_name="initialcontract", verbose_name="Eskalaun")
	date_start = models.DateField(null=True, verbose_name="Data Hahu")
	file = models.FileField(upload_to=upload_initial_contract, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexu Despacho")
	disp_number = models.CharField(max_length=50, null=True, blank=True, verbose_name="Numeru Despacho")
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	hashed = models.CharField(max_length=32, null=True)

	def __str__(self):
		template = '{0.employee}'
		return template.format(self)

class Contract(models.Model):
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='contract', verbose_name="Pessoal")
	contract_type = models.ForeignKey(ContractType, on_delete=models.CASCADE, null=True, blank=True, related_name="contract", verbose_name="RJS")
	category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name="contract", verbose_name="Kategoria")
	grade = models.ForeignKey(Grade, on_delete=models.CASCADE, null=True, blank=True, related_name="contract", verbose_name="Grau")
	echelon = models.ForeignKey(Echelon, on_delete=models.CASCADE, null=True, blank=True, related_name="contract", verbose_name="Eskalaun")
	is_active = models.BooleanField(default=True)
	is_lock = models.BooleanField(default=False, null=True)
	start_date = models.DateField(null=True, verbose_name="Data Hahu")
	end_date = models.DateField(null=True, verbose_name="Data Remata Kontratu")
	terminate_date = models.DateField(null=True, verbose_name="Data Termina")
	is_prom = models.BooleanField(default=False, null=True, blank=True)
	prom_date = models.DateField(null=True, blank=True)
	is_prog = models.BooleanField(default=False, null=True, blank=True)
	prog_date = models.DateField(null=True, blank=True)
	reason = models.CharField(max_length=100, null=True, blank=True, verbose_name="Rajaun")
	file = models.FileField(upload_to=upload_contract, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexu Despacho")
	disp_number = models.CharField(max_length=50, null=True, blank=True, verbose_name="Numeru Despacho")

	dg = models.ForeignKey(DG, on_delete=models.CASCADE, null=True, blank=True, related_name="contract", verbose_name="Diresaun Geral")
	division = models.ForeignKey(Division, on_delete=models.CASCADE, null=True, blank=True, related_name="contract", verbose_name="Diresaun")
	department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, related_name="contract", verbose_name="Departamento")
	section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True, related_name="contract", verbose_name="Seksaun")
	gabinete = models.ForeignKey(Gabinete, on_delete=models.CASCADE, null=True, blank=True, related_name="contract", verbose_name="Gabinete")
	position = models.ForeignKey(Position, on_delete=models.CASCADE, null=True, blank=True, related_name="contract", verbose_name="Pojisaun")

	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	hashed = models.CharField(max_length=32, null=True)

	def __str__(self):
		template = '{0.category}'
		return template.format(self)

class ContractTypeProgress(models.Model):
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='contracttypeprogress', verbose_name="Pessoal")
	contract_type = models.ForeignKey(ContractType, on_delete=models.CASCADE, null=True, related_name="contracttypeprogress", verbose_name="RJS")
	start_date = models.DateField(null=True, verbose_name="Data Hahu")
	hashed = models.CharField(max_length=32, null=True)

class BasicSalary(models.Model):
	category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name="basicsalary", verbose_name="Kategoria")
	grade = models.ForeignKey(Grade, on_delete=models.CASCADE, null=True, blank=True, related_name="basicsalary", verbose_name="Grau")
	echelon = models.ForeignKey(Echelon, on_delete=models.CASCADE, null=True, blank=True, related_name="basicsalary", verbose_name="Eskalaun")
	amount = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Montante")

	def __str__(self):
		template = '{0.category} ({0.grade}/{0.echelon.code}) - {0.amount}'
		return template.format(self)

class PositionSalary(models.Model):
	position = models.ForeignKey(Position, on_delete=models.CASCADE, null=True, blank=True, related_name="positionsalary", verbose_name="Pojisaun")
	amount = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name="Montante")
	type = models.CharField(choices=[('A','A'),('B','B')], max_length=4, null=True, blank=True, verbose_name="Tipu")

	def __str__(self):
		template = '{0.type} - {0.position} - {0.amount}'
		return template.format(self)

class EmployeeSalary(models.Model):
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='empsalary', verbose_name="Pessoal")
	position = models.ForeignKey(Position, on_delete=models.CASCADE, null=True, blank=True, related_name="empsalary", verbose_name="Pojisaun")
	basic_salary = models.ForeignKey(BasicSalary, on_delete=models.CASCADE, null=True, blank=False, related_name="empsalary", verbose_name="Salariu Basico")
	position_salary = models.ForeignKey(PositionSalary, on_delete=models.CASCADE, null=True, blank=True, related_name="empsalary", verbose_name="Subsidiu Chefia")
	contract = models.ForeignKey(Contract, on_delete=models.CASCADE, null=True, blank=True, related_name="empsalary", verbose_name="Kontratu")
	transport = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Transporte")
	total = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name="Total")
	is_active = models.BooleanField(default=True)
	is_lock = models.BooleanField(default=True, null=True)
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	hashed = models.CharField(max_length=32, null=True)

	def __str__(self):
		template = '{0.basic_salary}'
		return template.format(self)

class Kolokasaun(models.Model):
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="kolokasaun")
	position = models.ForeignKey(Position, on_delete=models.CASCADE, null=True, related_name="kolokasaun")
	section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True, related_name="kolokasaun", verbose_name="Seksaun")
	department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, related_name="kolokasaun", verbose_name="Departamento")
	division = models.ForeignKey(Division, on_delete=models.CASCADE, null=True, blank=True, related_name="kolokasaun", verbose_name="Diresaun")
	dg = models.ForeignKey(DG, on_delete=models.CASCADE, null=True, blank=True, related_name="kolokasaun", verbose_name="Diresaun Geral")
	start_date = models.DateField(null=True, blank=True, verbose_name="Data Hahu")
	end_date = models.DateField(null=True, blank=True, verbose_name="Data Remata")
	end_reason = models.CharField(max_length=200, null=True, blank=True, verbose_name="Rajaun")
	is_active = models.BooleanField(default=True)
	is_confirm = models.BooleanField(default=False, null=True)
	file = models.FileField(upload_to=upload_koloka, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexu Despacho")
	disp_number = models.CharField(max_length=50, null=True, blank=True, verbose_name="Numeru Despacho")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	hashed = models.CharField(max_length=32, null=True)

	def __str__(self):
		template = '{0.position} {0.employee}'
		return template.format(self)
