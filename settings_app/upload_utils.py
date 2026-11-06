import os
from uuid import uuid4

def upload_estado(instance, filename):
	upload_to = 'employee_files/{}'.format(instance.id)
	field = 'estado'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}.{}'.format(field,instance.id,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_reforma(instance, filename):
	upload_to = 'reforma/{}'.format(instance.id)
	field = 'reforma'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}.{}'.format(field,instance.id,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_karta(instance, filename):
	upload_to = 'karta/{}'.format(instance.id)
	field = 'karta'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}.{}'.format(field,instance.id,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_estagio(instance, filename):
	upload_to = 'estagio/{}'.format(instance.id)
	field = 'estagio'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}.{}'.format(field,instance.id,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_photo(instance, filename):
	upload_to = 'employee_files/{}'.format(instance.employee.id)
	field = 'photo'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}.{}'.format(field,instance.employee.id,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_formal(instance, filename):
	upload_to = 'employee_files/{}/formal/'.format(instance.employee.id)
	field = 'formal'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.employee.id,instance.pk,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_nonformal(instance, filename):
	upload_to = 'employee_files/{}/nonformal'.format(instance.employee.id)
	field = 'nonformal'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.employee.id,instance.pk,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_depend(instance, filename):
	upload_to = 'employee_files/{}/depend'.format(instance.employee.id)
	field = 'depend'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.employee.id,instance.pk,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_attendace(instance, filename):
	upload_to = 'absensia/{}/{}'.format(instance.div.id, instance.year)
	field = 'absensia'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.year,instance.month,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_perform(instance, filename):
	upload_to = 'employee_files/{}/avaliasaun/'.format(instance.employee.id)
	field = 'avaliasaun'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.id,instance.year,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_penas(instance, filename):
	upload_to = 'employee_files/{}/penas_louvores/'.format(instance.employee.id)
	field = 'penas'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.id,instance.date,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_louvores(instance, filename):
	upload_to = 'employee_files/{}/penas_louvores/'.format(instance.employee.id)
	field = 'louvores'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.id,instance.date,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_destaka(instance, filename):
	upload_to = 'employee_files/{}/mrjt/'.format(instance.employee.id)
	field = 'destaka'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.id,instance.start_date,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_trasfer(instance, filename):
	upload_to = 'employee_files/{}/mrjt/'.format(instance.employee.id)
	field = 'trasfer'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.id,instance.datetime,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_initial_contract(instance, filename):
	upload_to = 'employee_files/{}/contract/'.format(instance.employee.id)
	field = 'initial'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.id,instance.date_start,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_contract(instance, filename):
	upload_to = 'employee_files/{}/contract/'.format(instance.employee.id)
	field = 'actual'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.id,instance.start_date,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_nom(instance, filename):
	upload_to = 'employee_files/{}/nomeasaun/'.format(instance.employee.id)
	field = 'nom'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.id,instance.start_date,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_koloka(instance, filename):
	upload_to = 'employee_files/{}/koloka/'.format(instance.employee.id)
	field = 'koloka'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.id,instance.start_date,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_promotion(instance, filename):
	upload_to = 'employee_files/{}/promotion/'.format(instance.employee.id)
	field = 'promotion'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.id,instance.start_date,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_training(instance, filename):
	upload_to = 'employee_files/{}/training/'.format(instance.employee.id)
	field = 'training'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.id,instance.start_date,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_retire(instance, filename):
	upload_to = 'employee_files/{}/retire/'.format(instance.employee.id)
	field = 'retire'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}.{}'.format(field,instance.id,instance.retire_date,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_leave(instance, filename):
	upload_to = 'employee_files/{}/licenca/'.format(instance.employee.id)
	field = 'licenca'
	ext = filename.split('.')[-1]
	if instance.pk:
		filename = '{}_{}_{}_{}.{}'.format(field,instance.id,instance.leave_type.code.lower(),instance.start_date,ext)
	else:
		filename = '{}.{}'.format(uuid4().hex, ext)
	return os.path.join(upload_to, filename)

def upload_id_card(instance, filename):
	upload_to = 'employee_files/{}/idcards/'.format(instance.employee.id)
	ext = filename.split('.')[-1]
	filename = '{}_{}.{}'.format(uuid4().hex,instance.employee.id,ext)
	return os.path.join(upload_to, filename)
