from django.contrib import admin

from . import models

for name in ('Minister', 'DG', 'Division', 'Department', 'Section', 'Gabinete', 'Position', 'EducationLevel',
		'Country', 'Municipality', 'AdministrativePost', 'Village', 'ContractType', 'Status', 'Language', 'Year'):
	admin.site.register(getattr(models, name))
