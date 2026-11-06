from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from attendance.models import AttendanceStatus
from leave.models import LeaveType

GROUPS = ['admin', 'staff', 'president', 'funsionario', 'employee']
STATUS = [('F', 'Falta'), ('P', 'Presensa'), ('L', 'Lisensa')]


class Command(BaseCommand):
	help = 'Siapkan data awal: grup pengguna dan status absensi (F/P/L). Aman dijalankan berulang kali.'

	def handle(self, *args, **opts):
		for name in GROUPS:
			_, new = Group.objects.get_or_create(name=name)
			self.stdout.write('%s grup %s' % ('Buat' if new else 'Ada ', name))
		# urutan ID 1,2,3 = F,P,L seperti database lama (ATTENDANCE_ACTIVE_STATUS_ID dipakai oleh modul QR)
		if not AttendanceStatus.objects.exists():
			for code, name in STATUS:
				AttendanceStatus.objects.create(code=code, name=name)
			self.stdout.write('Buat status absensi F, P, L')
		if not LeaveType.objects.exists():
			LeaveType.objects.create(code='L', name='Lisensa')
		self.stdout.write(self.style.SUCCESS('Selesai. Buat superuser: python manage.py createsuperuser'))
