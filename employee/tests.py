

# ----------------------------------------------------------------- impor daftar staf
import csv as _csv  # noqa: E402
import os as _os  # noqa: E402
import tempfile as _tempfile  # noqa: E402

from django.contrib.auth.models import User as _User  # noqa: E402
from django.core.management import call_command as _call  # noqa: E402
from django.core.management.base import CommandError as _CommandError  # noqa: E402
from django.test import TestCase as _TestCase  # noqa: E402

from attendance.models_qr import QRCard as _QRCard  # noqa: E402
from custom.models import DG as _DG, Division as _Division, Position as _Position, Status as _Status  # noqa: E402
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
		self.assertEqual((d.division.name, d.dg.name), ('Program Nasional', 'Mata Dalan Institute (MDI)'))
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
		self.assertEqual(_DG.objects.count(), 1)

	def test_dry_run_saves_nothing(self):
		out = self.run_cmd(self.csv(self.ROWS), '--dry-run')
		self.assertIn('SIMULASI', out)
		for model in (_Employee, _Position, _Division, _DG, _QRCard):
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

	def test_custom_dg_and_example_file_in_repo(self):
		from django.conf import settings
		self.run_cmd(self.csv(self.ROWS[:1]), '--dg', 'DG Lain')
		self.assertEqual(_ED.objects.get().dg.name, 'DG Lain')
		_Employee.objects.all().delete()
		example = _os.path.join(settings.BASE_DIR, 'employee/data/staff_example.csv')
		self.assertIn('2 baru', self.run_cmd(example))
