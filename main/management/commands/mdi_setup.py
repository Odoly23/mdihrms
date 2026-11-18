from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

import datetime

from attendance.models import AttendanceStatus, Month, Year
from leave.models import LeaveType

from main import groups as grp

STATUS = [('F', 'Falta'), ('P', 'Presensa'), ('L', 'Lisensa')]


class Command(BaseCommand):
	help = 'Siapkan data awal: grup pengguna dan status absensi (F/P/L). Aman dijalankan berulang kali.'

	def handle(self, *args, **opts):
		for name in grp.GROUPS:
			_, new = Group.objects.get_or_create(name=name)
			if opts.get('verbosity', 1) > 0:
				self.stdout.write('%s grup %s' % ('Buat' if new else 'Ada ', name))
		moved = grp.migrate_legacy()          # president/hr/logistik/resepsionis/funsionario/employee -> 4 grup baru
		if moved and opts.get('verbosity', 1) > 0:
			self.stdout.write('Pindahkan %d keanggotaan grup lama ke grup baru' % moved)
		# urutan ID 1,2,3 = F,P,L seperti database lama (ATTENDANCE_ACTIVE_STATUS_ID dipakai oleh modul QR)
		if not AttendanceStatus.objects.exists():
			for code, name in STATUS:
				AttendanceStatus.objects.create(code=code, name=name)
			if opts.get('verbosity', 1) > 0:
				self.stdout.write('Buat status absensi F, P, L')
		self._seed_programs()
		self._seed_calendar(opts)
		self._seed_categories()
		if not LeaveType.objects.exists():
			LeaveType.objects.create(code='L', name='Lisensa')
		if opts.get('verbosity', 1) > 0:
			self.stdout.write(self.style.SUCCESS('Selesai. Buat superuser: python manage.py createsuperuser'))

	def _seed_programs(self):
		"""Unit organisasi tunggal ('Program', model Division) sesuai daftar staf MDI. Aman dijalankan berulang."""
		from custom.models import Division
		for code, name in (('PN', 'Program Nasional'), ('ISIS', 'ISIS - Programs ASEAN Think Tank')):
			if not Division.objects.filter(name=name).exists():
				Division.objects.create(code=code, name=name)

	def _seed_calendar(self, opts):
		"""12 bulan (nama Tetun) dan tahun berjalan -1..+1; yang berjalan diaktifkan bila belum ada yang aktif."""
		from attendance.qr_i18n import MONTHS
		today = datetime.date.today()
		for code in range(1, 13):
			Month.objects.get_or_create(code=code, defaults={'name': MONTHS['tet'][code - 1]})
		for y in (today.year - 1, today.year, today.year + 1):
			Year.objects.get_or_create(year=y)
		if not Month.objects.filter(is_active=True).exists():
			Month.objects.filter(code=today.month).update(is_active=True)
		if not Year.objects.filter(is_active=True).exists():
			Year.objects.filter(year=today.year).update(is_active=True)

	def _seed_categories(self):
		"""Kategori aset bawaan; namanya diterjemahkan otomatis lewat kode (nama Inggris disimpan sebagai cadangan)."""
		from assets.models import AssetCategory
		for code, name in (('computer', 'Computer'), ('laptop', 'Laptop'), ('printer', 'Printer'), ('monitor', 'Monitor'),
				('phone', 'Phone'), ('scanner', 'Scanner'), ('other', 'Other')):
			AssetCategory.objects.get_or_create(code=code, defaults={'name': name})
