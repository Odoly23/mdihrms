from django.contrib import admin

from . import models

for name in ('Minister', 'Division', 'Gabinete', 'Position', 'EducationLevel',
		'Country', 'Municipality', 'AdministrativePost', 'Village', 'ContractType', 'Status', 'Language', 'Year'):
	admin.site.register(getattr(models, name))
