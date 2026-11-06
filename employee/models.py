import datetime
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db.models import base
from custom.models import DG, Division, Department, Gabinete, Position, Country, Municipality, AdministrativePost,\
	Section, Status, Village, EducationLevel, University, Faculty, StudyProgram, Area, Language, ContractType
from settings_app.upload_utils import upload_photo, upload_formal, upload_nonformal, upload_id_card,\
	upload_depend, upload_estado

class Employee(models.Model):
	first_name = models.CharField(max_length=30, null=True, verbose_name="Naran")
	last_name = models.CharField(max_length=30, null=True, blank=True, verbose_name="Apelidu")
	place_of_birth = models.CharField(max_length=100, blank=True, null=True, verbose_name="Fatin Moris")
	date_of_birth = models.DateField(null=True, verbose_name="Data Moris")
	sex = models.CharField(choices=[('Mane','Mane'),('Feto','Feto')], max_length=6, null=True, blank=True, verbose_name="Sexu")
	marital = models.CharField(choices=[('Solteiro/a','Solteiro/a'),('Casado/a','Casado/a'),('Divorciado/a','Divorciado/a'),('Viuvo/a','Viuvo/a')], max_length=15, null=True, blank=True, verbose_name="Estado Civil")
	ran = models.CharField(choices=[('A','A'),('B','B'),('AB','AB'),('O','O'),('A+','A+'),('B+','B+'),('O+','O+')], max_length=15, null=True, blank=True, verbose_name="Grupu Ran")
	country = models.ForeignKey(Country, on_delete=models.CASCADE, null=True, verbose_name="Nasionalidade")
	father = models.CharField(max_length=100, null=True, blank=True, verbose_name="Aman")
	mother = models.CharField(max_length=100, null=True, blank=True, verbose_name="Inan")
	status = models.ForeignKey(Status, on_delete=models.CASCADE, null=True, verbose_name="Status")
	file = models.FileField(upload_to=upload_estado, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexa Estado Civil")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	hashed = models.CharField(max_length=32, null=True)
	
	def __str__(self):
		template = '{0.first_name} {0.last_name}'
		return template.format(self)
	def age(self):
		return int(round((datetime.date.today() - self.date_of_birth).days/365.2425,0))

class IDFNumber(models.Model):
	employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='idfnumber')
	contract_type = models.ForeignKey(ContractType, on_delete=models.CASCADE, null=True, blank=True, related_name="idfnumber", verbose_name="RJS")
	nrf = models.CharField(max_length=30, null=True, blank=True, verbose_name="Nu. PMIS/NRF")
	date_entry = models.DateField(null=True, blank=True)
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	def __str__(self):
		template = '{0.nrf}'
		return template.format(self)

class IDNumbers(models.Model):
	employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='idnumbers')
	niss = models.CharField(max_length=30, null=True, blank=True, verbose_name="NISS")
	payrol_number = models.CharField(max_length=30, null=True, blank=True, verbose_name="Payrol")
	bank_account = models.CharField(max_length=30, null=True, blank=True, verbose_name="Konta Bankaria")
	bank_name = models.CharField(max_length=30, null=True, blank=True, verbose_name="Banku")
	iban = models.CharField(max_length=30, null=True, blank=True)
	file = models.FileField(upload_to=upload_id_card, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexa Konta Bankaria")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

	def __str__(self):
		template = '{0.niss} | {0.payrol_number} - {0.iban}'
		return template.format(self)

class LIDNumbers(models.Model):
	employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='lidnumbers')
	electoral = models.CharField(max_length=30, null=True, blank=False, verbose_name="Eleitoral")
	elec_expiry_date = models.DateField(null=True, blank=True, verbose_name="Valido too")
	bi = models.CharField(max_length=30, null=True, blank=True, verbose_name="BI")
	bi_expiry_date = models.DateField(null=True, blank=True, verbose_name="Valido too")
	passport = models.CharField(max_length=15, null=True, blank=True, verbose_name="Pasaporte")
	pass_expiry_date = models.DateField(null=True, blank=True, verbose_name="Valido too")
	cert_rdtl = models.CharField(max_length=30, null=True, blank=True, verbose_name="Certidaun RDTL")
	file_el = models.FileField(upload_to=upload_id_card, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexu Eleitoral")
	file_bi = models.FileField(upload_to=upload_id_card, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexu BI")
	file_pas = models.FileField(upload_to=upload_id_card, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexu Pasaporte")
	file_cert = models.FileField(upload_to=upload_id_card, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexu Certidaun RDTL")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

	def __str__(self):
		template = '{0.electoral}'
		return template.format(self)

class IIDNumbers(models.Model):
	employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='iidnumbers')
	passport = models.CharField(max_length=15, null=True, blank=True, verbose_name="Pasaporte")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

	def __str__(self):
		template = '{0.passport}'
		return template.format(self)

class ContactInfo(models.Model):
	employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='contactinfo')
	email = models.CharField(max_length=50, null=True, blank=True)
	phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Nu. Telemovel")
	emergency_call = models.CharField(max_length=20, null=True, blank=True, verbose_name="Contacto Emergencia")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

	def __str__(self):
		template = '{0.employee} {0.email} {0.phone}'
		return template.format(self)

class LocationTL(models.Model):
	employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='locationtl')
	municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Municipiu")
	administrativepost = models.ForeignKey(AdministrativePost, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Posto")
	village = models.ForeignKey(Village, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Suco")
	aldeia = models.CharField(max_length=50, null=True, blank=True, verbose_name="Aldeia")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

	def __str__(self):
		template = '{0.employee} {0.municipality}'
		return template.format(self)

class AddressTL(models.Model):
	employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='addresstl')
	address = models.CharField(max_length=50, null=True, blank=True, verbose_name="Hela Fatin")
	municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Municipiu")
	administrativepost = models.ForeignKey(AdministrativePost, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Posto")
	village = models.ForeignKey(Village, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Suco")
	aldeia = models.CharField(max_length=50, null=True, blank=True, verbose_name="Aldeia")
	latitude = models.CharField(max_length=20, null=True, blank=True)
	longitude = models.CharField(max_length=20, null=True, blank=True)
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	
	def __str__(self):
		template = '{0.employee} {0.address}'
		return template.format(self)

class AddressOrigin(models.Model):
	employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='addressorigin')
	city = models.CharField(max_length=50, null=True, blank=True, verbose_name="Cidade")
	address = models.CharField(max_length=50, null=True, blank=True, verbose_name="Enderesu")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	
	def __str__(self):
		template = '{0.employee} {0.city}'
		return template.format(self)

class Photo(models.Model):
	employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='photo')
	image = models.ImageField(default='default.png', upload_to=upload_photo, null=True)
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	
	def __str__(self):
		template = '{0.employee}'
		return template.format(self)

class DriverLicence(models.Model):
	employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='driverlicence')
	number = models.CharField(max_length=30, null=True, blank=True, verbose_name="Numeru")
	type = models.CharField(max_length=30, null=True, blank=True, verbose_name="Tipu")
	expiry_date = models.DateField(max_length=15, null=True, blank=True, verbose_name="validade ate")
	file = models.FileField(upload_to=upload_id_card, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexu")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

	def __str__(self):
		template = '{0.number}'
		return template.format(self)

class FormalEducation(models.Model):
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="formaleducation")
	educationlevel = models.ForeignKey(EducationLevel, on_delete=models.CASCADE, related_name="formaleducation", verbose_name="Nivel Edukasaun")
	university = models.ForeignKey(University, null=True, blank=True, on_delete=models.CASCADE, related_name="formaleducation", verbose_name="Universidade/Entidade")
	faculty = models.CharField(max_length=100, null=True, blank=True, verbose_name="Faculdade")
	studyprogram = models.CharField(max_length=100, null=True, blank=True, verbose_name="Programa Estudu/Curso")
	area =  models.CharField(max_length=200, null=True, blank=True, verbose_name="Area Professional")
	graduation_year = models.DateField(null=True, blank=True, verbose_name="Data Gradua")
	summary = models.TextField(null=True, blank=True, verbose_name="Sumariu")
	file = models.FileField(upload_to=upload_formal, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexu Certificado")
	is_active = models.BooleanField(default=True)
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	hashed = models.CharField(max_length=32, null=True)
	
	def __str__(self):
		template = '{0.employee} {0.educationlevel}'
		return template.format(self)

class NonFormalEducation(models.Model):
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="nonformaleducation")
	title = models.CharField(max_length=500, null=True, blank=True, verbose_name="Titulu")
	tutelary_entity = models.CharField(max_length=100, null=True, blank=True, verbose_name="Fatin")
	start_date = models.DateField(null=True, blank=True, verbose_name="Data Hahu")
	end_date = models.DateField(null=True, blank=True, verbose_name="Data Remata")
	hours = models.IntegerField(null=True, blank=True, verbose_name="Total Horas")
	area = models.CharField(max_length=200, null=True, blank=True, verbose_name="Area")
	summary = models.TextField(null=True, blank=True, verbose_name="Sumariu")
	file = models.FileField(upload_to=upload_nonformal, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexu Certificado")
	is_active = models.BooleanField(default=True)
	traning_id = models.IntegerField(null=True, blank=True)
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	hashed = models.CharField(max_length=32, null=True)

	def __str__(self):
		template = '{0.employee} {0.course_type}'
		return template.format(self)

class WorkExperience(models.Model):
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="workexperience")
	instituisaun = models.CharField(max_length=100, null=True, blank=True)
	dg = models.CharField(max_length=100, null=True, blank=True)
	diresaun = models.CharField(max_length=100, null=True, blank=True)
	departamentu = models.CharField(max_length=100, null=True, blank=True)
	seksaun = models.CharField(max_length=100, null=True, blank=True)
	pojisaun = models.CharField(max_length=50, null=True, blank=True)
	kategoria = models.CharField(max_length=50, null=True, blank=True)
	grau = models.CharField(max_length=20, null=True, blank=True)
	eskalaun = models.IntegerField(null=True, blank=True)
	start_date = models.DateField(null=True, verbose_name="Data Hahu")
	end_date = models.DateField(null=True, verbose_name="Data Remata")
	municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Municipiu")
	administrativepost = models.ForeignKey(AdministrativePost, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Posto")
	village = models.ForeignKey(Village, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Suco")
	aldeia = models.CharField(max_length=50, null=True, blank=True, verbose_name="Aldeia")
	is_active = models.BooleanField(default=True)
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	hashed = models.CharField(max_length=32, null=True)

	def __str__(self):
		template = '{0.instituisaun}'
		return template.format(self)

class EmployeeDependency(models.Model):
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="employeedependency")
	first_name = models.CharField(max_length=50, null=True, verbose_name="Naran Propio")
	last_name = models.CharField(max_length=50, null=True, verbose_name="Apelidu")
	place_of_birth = models.CharField(max_length=100, blank=True, null=True, verbose_name="Fatin Moris")
	date_of_birth = models.DateField(null=True, verbose_name="Data Moris")
	sex = models.CharField(choices=[('Mane','Mane'),('Feto','Feto')], max_length=6, null=True, blank=True, verbose_name="Sexu")
	type = models.CharField(choices=[('Conjuge','Conjuge'),('Decendente','Decendente')], max_length=10, null=True, blank=True, verbose_name="Tipu")
	relation = models.CharField(choices=[\
				('Aman','Aman'),('Inan','Inan'),('Laen','Laen'),\
				('Fen','Fen'),('Oan','Oan'),('Seluk','Seluk')
			], max_length=7, null=True, blank=True, verbose_name="Relasaun")
	file = models.FileField(upload_to=upload_depend, null=True, blank=True,
			validators=[FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name="Anexu")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	hashed = models.CharField(max_length=32, null=True)
	def __str__(self):
		template = '{0.first_name} {0.last_name}'
		return template.format(self)

class EmployeeLanguage(models.Model):
	employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="employeelanguage")
	language = models.ForeignKey(Language, on_delete=models.CASCADE, null=True, blank=True, related_name="employeelanguage")
	koalia = models.CharField(choices=[('Diak','Diak'),('Naton','Naton'),('Ladiak','Ladiak')], max_length=15, null=True, blank=True, verbose_name="Koalia")
	lee = models.CharField(choices=[('Diak','Diak'),('Naton','Naton'),('Ladiak','Ladiak')], max_length=15, null=True, blank=True, verbose_name="Lee")
	hakerek = models.CharField(choices=[('Diak','Diak'),('Naton','Naton'),('Ladiak','Ladiak')], max_length=15, null=True, blank=True, verbose_name="Hakerek")
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	hashed = models.CharField(max_length=32, null=True)
	def __str__(self):
		template = '{0.employee} {0.language}'
		return template.format(self)

class EmployeeUser(models.Model):
	employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="employeeuser")
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	
	def __str__(self):
		template = '{0.employee} {0.user}'
		return template.format(self)

class EmployeeCard(models.Model):
	employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="employeecard")
	issue_date = models.DateField(null=True, verbose_name="Data Imprimi")
	expiry_date = models.DateField(null=True, verbose_name="Data validade")
	is_active = models.BooleanField(default=True)
	is_printed = models.BooleanField(default=False)
	datetime = models.DateTimeField(null=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
	
	def __str__(self):
		template = '{0.employee} {0.is_printed}'
		return template.format(self)

class EmployeePosition(models.Model):
	employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="employeeposition", verbose_name="Pessoal")
	position = models.ForeignKey(Position, on_delete=models.CASCADE, null=True, blank=True, related_name="employeeposition", verbose_name="Pojisaun")
	
	def __str__(self):
		template = '{0.position}'
		return template.format(self)

class EmployeeDivision(models.Model):
	employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="employeedivision", verbose_name="Pessoal")
	dg = models.ForeignKey(DG, on_delete=models.CASCADE, null=True, blank=True, related_name="employeedivision", verbose_name="Diresaun Geral")
	division = models.ForeignKey(Division, on_delete=models.CASCADE, null=True, blank=True, related_name="employeedivision", verbose_name="Diresaun")
	department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True, related_name="employeedivision", verbose_name="Departamento")
	section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True, related_name="employeedivision", verbose_name="Seksaun")
	gabinete = models.ForeignKey(Gabinete, on_delete=models.CASCADE, null=True, blank=True, related_name="employeedivision", verbose_name="Gabinete")
	def __str__(self):
		template = '{0.employee}'
		return template.format(self)
