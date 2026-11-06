from django.contrib import admin

from . import models

for name in ('InitialContract', 'Contract', 'ContractTypeProgress', 'BasicSalary', 'PositionSalary',
		'EmployeeSalary', 'Kolokasaun'):
	admin.site.register(getattr(models, name))
