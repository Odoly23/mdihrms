from django.contrib import admin

from . import models

admin.site.register(models.Employee)
for name in ('EmployeePosition', 'EmployeeDivision', 'Photo', 'EmployeeUser', 'EmployeeCard', 'IDFNumber',
		'ContactInfo'):
	admin.site.register(getattr(models, name))
