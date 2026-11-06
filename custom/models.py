import hashlib
from django.db import models

class Minister(models.Model):
	code = models.CharField(max_length=10, null=True, blank=True)
	name = models.CharField(max_length=50, verbose_name="Naran")
	hashed = models.CharField(max_length=32, null=True, blank=True)

	def __str__(self):
		template = '{0.name}'
		return template.format(self)

	def save(self, *args, **kwargs):
		self.hashed = hashlib.md5(str(self.id).encode()).hexdigest()
		return super(Minister, self).save(*args, **kwargs)

class DG(models.Model):
	code = models.CharField(max_length=10, null=True, blank=True)
	name = models.CharField(max_length=100, verbose_name="Naran")
	hashed = models.CharField(max_length=32, null=True, blank=True)

	def __str__(self):
		template = '{0.name}'
		return template.format(self)
	def save(self, *args, **kwargs):
		self.hashed = hashlib.md5(str(self.id).encode()).hexdigest()
		return super(DG, self).save(*args, **kwargs)

class Division(models.Model):
	dg = models.ForeignKey(DG, on_delete=models.CASCADE, null=True, blank=True)
	code = models.CharField(max_length=10, null=True, blank=True)
	name = models.CharField(max_length=100, verbose_name="Naran")
	hashed = models.CharField(max_length=32, null=True, blank=True)
	def __str__(self):
		template = '{0.name}'
		return template.format(self)
	def save(self, *args, **kwargs):
		self.hashed = hashlib.md5(str(self.id).encode()).hexdigest()
		return super(Division, self).save(*args, **kwargs)

class Department(models.Model):
	division = models.ForeignKey(Division, on_delete=models.CASCADE, null=True)
	code = models.CharField(max_length=10, null=True, blank=True)
	name = models.CharField(max_length=100, verbose_name="Naran")
	hashed = models.CharField(max_length=32, null=True, blank=True)
	def __str__(self):
		template = '{0.name}'
		return template.format(self)
	def save(self, *args, **kwargs):
		self.hashed = hashlib.md5(str(self.id).encode()).hexdigest()
		return super(Department, self).save(*args, **kwargs)

class Section(models.Model):
	department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True)
	name = models.CharField(max_length=100, verbose_name="Naran")
	hashed = models.CharField(max_length=32, null=True, blank=True)
	def __str__(self):
		template = '{0.name}'
		return template.format(self)
	def save(self, *args, **kwargs):
		self.hashed = hashlib.md5(str(self.id).encode()).hexdigest()
		return super(Section, self).save(*args, **kwargs)

class Gabinete(models.Model):
	code = models.CharField(max_length=10, null=True, blank=True)
	name = models.CharField(max_length=100, verbose_name="Naran")
	hashed = models.CharField(max_length=32, null=True, blank=True)

	def __str__(self):
		template = '{0.name}'
		return template.format(self)
	def save(self, *args, **kwargs):
		self.hashed = hashlib.md5(str(self.id).encode()).hexdigest()
		return super(Gabinete, self).save(*args, **kwargs)

class Position(models.Model):
	name = models.CharField(max_length=100, verbose_name="Naran")
	def __str__(self):
		template = '{0.name}'
		return template.format(self)

class EducationLevel(models.Model):
	name = models.CharField(max_length=100, verbose_name="Naran")
	def __str__(self):
		template = '{0.name}'
		return template.format(self)

class Country(models.Model):
	code = models.CharField(max_length=5)
	name = models.CharField(max_length=50, verbose_name="Naran")

	def __str__(self):
		template = '{0.name}'
		return template.format(self)

class Municipality(models.Model):
	code = models.CharField(max_length=5, null=True)
	name = models.CharField(max_length=100, verbose_name="Naran")
	hckey = models.CharField(max_length=10, null=True)

	def __str__(self):
		template = '{0.name}'
		return template.format(self)

class AdministrativePost(models.Model):
	municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE, null=True)
	name = models.CharField(max_length=100, verbose_name="Naran")
	def __str__(self):
		template = '{0.name}'
		return template.format(self)

class Village(models.Model):
	administrativepost = models.ForeignKey(AdministrativePost, on_delete=models.CASCADE, null=True)
	name = models.CharField(max_length=100, verbose_name="Naran")
	def __str__(self):
		template = '{0.name}'
		return template.format(self)

class University(models.Model):
	country = models.ForeignKey(Country, on_delete=models.CASCADE, null=True)
	name = models.CharField(max_length=100, verbose_name="Naran")
	def __str__(self):
		template = '{0.name}'
		return template.format(self)

class Faculty(models.Model):
	name = models.CharField(max_length=100, verbose_name="Naran")
	def __str__(self):
		template = '{0.name}'
		return template.format(self)

class StudyProgram(models.Model):
	name = models.CharField(max_length=100, verbose_name="Naran")
	def __str__(self):
		template = '{0.name}'
		return template.format(self)

class Area(models.Model):
	name = models.CharField(max_length=100, verbose_name="Naran")
	def __str__(self):
		template = '{0.name}'
		return template.format(self)

class ContractType(models.Model):
	name = models.CharField(max_length=100, verbose_name="Naran")
	def __str__(self):
		template = '{0.name}'
		return template.format(self)

class Status(models.Model):
	name = models.CharField(max_length=100, verbose_name="Naran")
	def __str__(self):
		template = '{0.name}'
		return template.format(self)

class Category(models.Model):
	name = models.CharField(max_length=100, verbose_name="Naran")
	def __str__(self):
		template = '{0.name}'
		return template.format(self)

class Grade(models.Model):
	category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)
	name = models.CharField(max_length=100, verbose_name="Naran")
	def __str__(self):
		template = '{0.name}'
		return template.format(self)

class Echelon(models.Model):
	code = models.CharField(max_length=10)
	name = models.CharField(max_length=10)

	def __str__(self):
		template = '{0.code}'
		return template.format(self)

class Institute(models.Model):
	code = models.CharField(max_length=20, null=True, blank=True)
	name = models.CharField(max_length=100, null=True, blank=True)
	phone = models.CharField(max_length=20, null=True, blank=True)
	email = models.CharField(max_length=20, null=True, blank=True)
	website = models.CharField(max_length=20, null=True, blank=True)
	address = models.CharField(max_length=100, null=True, blank=True)
	municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Municipiu")
	administrativepost = models.ForeignKey(AdministrativePost, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Posto")
	village = models.ForeignKey(Village, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Suco")
	aldeia = models.CharField(max_length=50, null=True, blank=True)
	is_active = models.BooleanField(default=False, null=True, blank=True)
	latitude = models.CharField(max_length=20, null=True, blank=True)
	longitude = models.CharField(max_length=20, null=True, blank=True)
	image = models.ImageField(default='logo.png', upload_to='custom_images/', null=True, blank=True)
	hashed = models.CharField(max_length=32, null=True, blank=True)
	def __str__(self):
		template = '{0.name} ({0.code})'
		return template.format(self)

	def save(self, *args, **kwargs):
		self.hashed = hashlib.md5(str(self.id).encode()).hexdigest()
		return super(Institute, self).save(*args, **kwargs)

class Year(models.Model):
	year = models.IntegerField(null=True, blank=True)
	is_active = models.BooleanField(default=False)
	def __str__(self):
		template = '{0.year}'
		return template.format(self)

class Language(models.Model):
	name = models.CharField(max_length=100, verbose_name="Lingua")
	def __str__(self):
		template = '{0.name}'
		return template.format(self)
