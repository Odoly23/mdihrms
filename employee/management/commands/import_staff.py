"""Impor daftar staf dari CSV (kolom: nama, posisi, diresaun = program/unit). Aman dijalankan berulang kali: staf yang sudah ada
(dicocokkan dari nama) hanya diperbarui posisinya/diresaun-nya, tidak digandakan.

    python manage.py import_staff data/staff_mdi.csv --dry-run     # lihat rencana dulu
    python manage.py import_staff data/staff_mdi.csv               # lalu jalankan

Yang dibuat per orang: Employee (aktif), EmployeePosition, EmployeeDivision, dan kartu QR. Dengan --accounts juga akun login
(nama pengguna dari nama, kata sandi awal DEFAULT_PASSWORD, wajib diganti saat login pertama, grup dari jabatan; admin sistem tidak
pernah diberikan otomatis). NRF, tanggal lahir, dan kontak tidak ada di daftar: lengkapi lewat menu Funsionariu > Hadia."""
import csv
import hashlib

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from attendance.models_qr import QRCard
from custom.models import Division, Position, Status
from employee.models import Employee, EmployeeDivision, EmployeePosition

ACTIVE_STATUS = 1
_MAX = {'first_name': 30, 'last_name': 30, 'position': 100, 'division': 100}


def split_name(full):
	"""'Maria Madalena Vicente' -> ('Maria', 'Madalena Vicente'); satu kata -> ('Adilson', '')."""
	parts = ' '.join(full.split()).split(' ', 1)
	return parts[0], (parts[1] if len(parts) > 1 else '')


class Command(BaseCommand):
	help = 'Impor daftar staf dari CSV (nama, posisi, diresaun).'

	def add_arguments(self, parser):
		parser.add_argument('csv_file')
		parser.add_argument('--dry-run', action='store_true', help='Hanya tampilkan rencana, tidak menyimpan apa pun')
		parser.add_argument('--accounts', action='store_true', help='Buat akun login untuk pegawai yang belum punya (kata sandi awal, wajib ganti)')

	def handle(self, *args, **o):
		rows = self._read(o['csv_file'])
		dry = o['dry_run']
		stats = {'new': 0, 'updated': 0, 'same': 0}
		with transaction.atomic():
			status = Status.objects.filter(pk=ACTIVE_STATUS).first() or Status.objects.create(pk=ACTIVE_STATUS, name='Ativu')
			for n, (name, pos_name, div_name) in enumerate(rows, 1):
				first, last = split_name(name)
				emp = Employee.objects.filter(first_name__iexact=first, last_name__iexact=last).first() if last else \
					Employee.objects.filter(first_name__iexact=first).filter(Q(last_name__isnull=True) | Q(last_name='')).first()
				position, _ = Position.objects.get_or_create(name=pos_name)
				division, _ = Division.objects.get_or_create(name=div_name)
				if emp is None:
					emp = Employee.objects.create(first_name=first, last_name=last, status=status,
						datetime=timezone.now())
					emp.hashed = hashlib.md5(str(emp.pk).encode()).hexdigest()
					emp.save(update_fields=['hashed'])
					stats['new'] += 1
					verb = 'BARU '
				else:
					cur_p = EmployeePosition.objects.filter(employee=emp).first()
					cur_d = EmployeeDivision.objects.filter(employee=emp).first()
					same = bool(cur_p and cur_p.position_id == position.pk and cur_d and cur_d.division_id == division.pk)
					stats['same' if same else 'updated'] += 1
					verb = 'SAMA ' if same else 'UBAH '
				EmployeePosition.objects.update_or_create(employee=emp, defaults={'position': position})
				EmployeeDivision.objects.update_or_create(employee=emp, defaults={'division': division})
				QRCard.objects.get_or_create(employee=emp, defaults={'datetime': timezone.now()})
				account = self._account(emp, first, last, pos_name) if o['accounts'] else ''
				self.stdout.write('%2d. %s %s %s — %s (%s)%s' % (n, verb, first, last, pos_name, div_name, account))
			if dry:
				transaction.set_rollback(True)
		self.stdout.write(self.style.SUCCESS('%s: %d baru, %d diubah, %d sama (%d baris).' % (
			'SIMULASI (tidak disimpan)' if dry else 'Selesai', stats['new'], stats['updated'], stats['same'], len(rows))))
		if not dry:
			self.stdout.write('Lengkapi NRF, tanggal lahir, dan kontak lewat Funsionariu > Hadia; cetak kartu di Absensi QR > Kartu QR.')

	def _account(self, emp, first, last, pos_name):
		"""Akun untuk pegawai yang belum punya: nama.pengguna dari nama (huruf kecil, tanpa aksen), kata sandi awal, wajib ganti."""
		from django.conf import settings
		from django.contrib.auth.models import Group, User
		from django.utils.text import slugify
		from employee.models import EmployeeUser
		from employee.services import _unique_username
		from main import middleware
		from main.groups import group_for_position
		from main.models import MustChangePassword
		link = EmployeeUser.objects.filter(employee=emp).select_related('user').first()
		if link:
			return ' [akun: %s, sudah ada]' % link.user.username
		base = '.'.join(p for p in (slugify(first), slugify(last.split(' ')[-1]) if last else '') if p) or 'emp%d' % emp.pk
		u = User.objects.create_user(_unique_username(base.replace('-', '')), password=settings.MDI_DEFAULT_PASSWORD)
		group = group_for_position(pos_name)
		u.groups.add(Group.objects.get_or_create(name=group)[0])
		EmployeeUser.objects.create(employee=emp, user=u)
		MustChangePassword.objects.update_or_create(user=u)
		middleware.set_flag(u.pk, True)
		return ' [akun baru: %s, grup %s]' % (u.username, group)

	def _read(self, path):
		try:
			f = open(path, newline='', encoding='utf-8-sig')
		except OSError as e:
			raise CommandError('Tidak bisa membuka %s: %s' % (path, e))
		with f:
			reader = csv.DictReader(f)
			need = {'nama', 'posisi', 'diresaun'}
			if not reader.fieldnames or not need <= {h.strip().lower() for h in reader.fieldnames}:
				raise CommandError('CSV harus punya kolom: nama, posisi, diresaun')
			rows, seen, errors = [], set(), []
			for i, raw in enumerate(reader, 2):
				r = {k.strip().lower(): (v or '').strip() for k, v in raw.items() if k}
				if not any(r.values()):
					continue
				name, pos, div = ' '.join(r['nama'].split()), r['posisi'], r['diresaun']
				if not name or not pos or not div:
					errors.append('baris %d: nama, posisi, dan diresaun wajib diisi' % i)
					continue
				first, last = split_name(name)
				for label, val in (('first_name', first), ('last_name', last), ('position', pos), ('division', div)):
					if len(val) > _MAX[label]:
						errors.append('baris %d: %s lebih dari %d karakter' % (i, label, _MAX[label]))
				key = name.lower()
				if key in seen:
					errors.append('baris %d: nama ganda (%s)' % (i, name))
				seen.add(key)
				rows.append((name, pos, div))
			if errors:
				raise CommandError('CSV tidak valid, tidak ada yang disimpan:\n  ' + '\n  '.join(errors))
		if not rows:
			raise CommandError('CSV kosong')
		return rows
