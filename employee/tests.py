

# ----------------------------------------------------------------- impor daftar staf
import csv as _csv  # noqa: E402
import os as _os  # noqa: E402
import tempfile as _tempfile  # noqa: E402

from django.contrib.auth.models import User as _User  # noqa: E402
from django.core.management import call_command as _call  # noqa: E402
from django.core.management.base import CommandError as _CommandError  # noqa: E402
from django.test import TestCase as _TestCase  # noqa: E402

from attendance.models_qr import QRCard as _QRCard  # noqa: E402
from custom.models import Division as _Division, Position as _Position, Status as _Status  # noqa: E402
from employee.models import Employee as _Employee, EmployeeDivision as _ED, EmployeePosition as _EP  # noqa: E402


class ImportStaffTests(_TestCase):
	def csv(self, rows, header=('nama', 'posisi', 'diresaun')):
		fd, path = _tempfile.mkstemp(suffix='.csv')
		with _os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
			w = _csv.writer(f)
			w.writerow(header)
			w.writerows(rows)
		self.addCleanup(_os.remove, path)
		return path

	def run_cmd(self, path, *a):
		from io import StringIO
		out = StringIO()
		_call('import_staff', path, *a, stdout=out)
		return out.getvalue()

	ROWS = [('Maria Madalena Vicente', 'Official Cleaner', 'Program Nasional'),
		('Adilson', 'Peskizador', 'ISIS - Programs ASEAN Think Tank'),
		('Durvalina de Fátima M. Pires', 'Volunteer', 'ISIS - Programs ASEAN Think Tank')]

	def test_creates_staff_positions_divisions_cards_but_no_accounts(self):
		out = self.run_cmd(self.csv(self.ROWS))
		self.assertIn('3 baru', out)
		self.assertEqual(_Employee.objects.count(), 3)
		m = _Employee.objects.get(first_name='Maria')
		self.assertEqual((m.last_name, m.status_id), ('Madalena Vicente', 1))
		self.assertEqual(_EP.objects.get(employee=m).position.name, 'Official Cleaner')
		d = _ED.objects.get(employee=m)
		self.assertEqual(d.division.name, 'Program Nasional')
		self.assertEqual(_QRCard.objects.count(), 3)
		self.assertEqual(_User.objects.count(), 0)                               # tidak ada akun login
		self.assertEqual(str(_Employee.objects.get(first_name='Adilson')), 'Adilson')     # satu kata saja: tanpa "None"
		self.assertEqual(_Employee.objects.get(first_name='Durvalina').last_name, 'de Fátima M. Pires')
		_Employee.objects.filter(first_name='Adilson').update(last_name=None)             # NULL lama pun dikenali di impor ulang
		self.assertIn('0 baru', self.run_cmd(self.csv(self.ROWS)))
		self.assertEqual(_Employee.objects.count(), 3)

	def test_idempotent_and_updates_changed_position(self):
		p = self.csv(self.ROWS)
		self.run_cmd(p)
		self.assertIn('0 baru, 0 diubah, 3 sama', self.run_cmd(p))
		changed = self.csv([('Adilson', 'Direktur', 'ISIS - Programs ASEAN Think Tank')] + self.ROWS[:1] + self.ROWS[2:])
		self.assertIn('0 baru, 1 diubah, 2 sama', self.run_cmd(changed))
		self.assertEqual(_Employee.objects.count(), 3)
		self.assertEqual(_EP.objects.get(employee__first_name='Adilson').position.name, 'Direktur')
		self.assertEqual(_QRCard.objects.count(), 3)
		self.assertEqual(_Division.objects.count(), 2)

	def test_dry_run_saves_nothing(self):
		out = self.run_cmd(self.csv(self.ROWS), '--dry-run')
		self.assertIn('SIMULASI', out)
		for model in (_Employee, _Position, _Division, _QRCard):
			self.assertEqual(model.objects.count(), 0, model)
		self.assertEqual(_Status.objects.count(), 0)

	def test_invalid_csv_is_rejected_whole(self):
		bad = self.csv([('A B', 'Staf', 'Div'), ('', 'Staf', 'Div'), ('A B', 'Staf', 'Div'), ('X' * 40, 'Staf', 'Div')])
		with self.assertRaises(_CommandError) as cm:
			self.run_cmd(bad)
		msg = str(cm.exception)
		self.assertIn('wajib diisi', msg)
		self.assertIn('nama ganda', msg)
		self.assertIn('lebih dari 30', msg)
		self.assertEqual(_Employee.objects.count(), 0)
		with self.assertRaises(_CommandError):
			self.run_cmd(self.csv([('A', 'B', 'C')], header=('name', 'job', 'div')))
		with self.assertRaises(_CommandError):
			self.run_cmd('/tidak/ada.csv')

	def test_example_file_in_repo(self):
		from django.conf import settings
		_Employee.objects.all().delete()
		example = _os.path.join(settings.BASE_DIR, 'employee/data/staff_example.csv')
		self.assertIn('2 baru', self.run_cmd(example))


class ImportAccountsTests(_TestCase):
	"""--accounts: akun dengan kata sandi awal, wajib ganti, grup dari jabatan; tidak pernah admin; tidak ganda bila diulang."""

	def setUp(self):
		from django.core.management import call_command
		call_command('mdi_setup', verbosity=0)

	def run_cmd(self, path, *extra):
		from io import StringIO
		from django.core.management import call_command
		out = StringIO()
		call_command('import_staff', path, *extra, stdout=out)
		return out.getvalue()

	def csv(self, rows):
		import tempfile
		f = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False, encoding='utf-8')
		f.write('nama,posisi,diresaun\n' + ''.join('%s,%s,%s\n' % r for r in rows))
		f.close()
		self.addCleanup(_os.remove, f.name)
		return f.name

	def test_accounts_created_once_with_groups_and_forced_change(self):
		from django.conf import settings
		from main.models import MustChangePassword
		path = self.csv([('Estevanus Coli', 'Director Ezekutivu MDI', 'Program Nasional'),
						 ('Anazita Maria', 'Assistente Adm & Finansa', 'Program Nasional'),
						 ('Maria Madalena Vicente', 'Official Cleaner', 'Program Nasional')])
		out = self.run_cmd(path, '--accounts')
		self.assertIn('estevanus.coli', out)
		users = {u.username: sorted(u.groups.values_list('name', flat=True)) for u in _User.objects.all()}
		self.assertEqual(users, {'estevanus.coli': ['director'], 'anazita.maria': ['administrasaun'], 'maria.vicente': ['staff']})
		u = _User.objects.get(username='maria.vicente')
		self.assertTrue(u.check_password(settings.MDI_DEFAULT_PASSWORD))
		self.assertEqual(MustChangePassword.objects.count(), 3)
		self.assertNotIn(settings.MDI_DEFAULT_PASSWORD, out)                     # kata sandi tidak dicetak
		self.run_cmd(path, '--accounts')
		self.assertEqual(_User.objects.count(), 3)

	def test_without_flag_no_accounts(self):
		self.run_cmd(self.csv([('Ana Lopes', 'Staf', 'Program Nasional')]))
		self.assertEqual(_User.objects.count(), 0)
