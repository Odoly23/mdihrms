from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from employee.models import Employee, EmployeeUser
from main import groups as grp


class Command(BaseCommand):
	help = ('Tetapkan grup pengguna (director / administrasaun / staff) dari jabatan pegawai. Tanpa --apply hanya menampilkan rencana. '
			'Admin sistem tidak pernah diubah dan tidak pernah diberikan otomatis. Aturan: main/groups.py (atau MDI_POSITION_GROUPS di settings).')

	def add_arguments(self, parser):
		parser.add_argument('--apply', action='store_true', help='benar-benar mengubah grup (bawaan: hanya tampilkan)')

	def handle(self, *args, **opts):
		new = grp.ensure_groups()
		grp.migrate_legacy()
		changes = 0
		for eu in EmployeeUser.objects.select_related('employee__employeeposition__position', 'user').order_by('employee__first_name'):
			u = eu.user
			have = set(u.groups.values_list('name', flat=True))
			if 'admin' in have:
				self.stdout.write('  %-28s admin (tidak diubah)' % eu.employee)
				continue
			pos = getattr(getattr(eu.employee, 'employeeposition', None), 'position', None)
			want = grp.group_for_position(pos.name if pos else '')
			now = have & set(grp.GROUPS)
			mark = '=' if now == {want} else '->'
			self.stdout.write('  %-28s %-34s %s %s' % (eu.employee, (pos.name if pos else '-')[:34], mark, want))
			if now != {want}:
				changes += 1
				if opts['apply']:
					u.groups.remove(*[new[n] for n in now])
					u.groups.add(new[want])
		self.stdout.write(self.style.SUCCESS('%d perubahan %s.' % (changes, 'diterapkan' if opts['apply'] else 'direncanakan (tambah --apply untuk menerapkan)')))
