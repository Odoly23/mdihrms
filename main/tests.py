from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from attendance.models import AttendanceStatus


class ProjectTests(TestCase):
	def test_setup_command_is_idempotent(self):
		call_command('mdi_setup', verbosity=0)
		call_command('mdi_setup', verbosity=0)
		self.assertEqual(Group.objects.count(), 6)
		self.assertEqual(list(AttendanceStatus.objects.order_by('id').values_list('code', flat=True)), ['F', 'P', 'L'])

	def test_login_required_and_login_page(self):
		self.assertEqual(self.client.get(reverse('home')).status_code, 302)
		self.assertContains(self.client.get(reverse('login')), 'MDI-HRMS')

	def test_home_for_each_group_and_without_group(self):
		call_command('mdi_setup', verbosity=0)
		for name in ('admin', 'staff', 'president', 'hr', 'funsionario', 'employee', None):
			u = User.objects.create_user('u_%s' % name, password='x')
			if name:
				u.groups.add(Group.objects.get(name=name))
			self.client.force_login(u)
			r = self.client.get(reverse('home'))
			self.assertEqual(r.status_code, 200, name)
			self.assertContains(r, '#e3171e')

	def test_logout_is_post_and_redirects_to_login(self):
		u = User.objects.create_user('x', password='x')
		self.client.force_login(u)
		r = self.client.post(reverse('logout'))
		self.assertRedirects(r, reverse('login'))

	def test_admin_menu_only_for_admin(self):
		call_command('mdi_setup', verbosity=0)
		a = User.objects.create_user('a', password='x'); a.groups.add(Group.objects.get(name='admin'))
		f = User.objects.create_user('f', password='x'); f.groups.add(Group.objects.get(name='funsionario'))
		self.client.force_login(a)
		self.assertContains(self.client.get(reverse('home')), reverse('qr-devices'))
		self.client.force_login(f)
		self.assertNotContains(self.client.get(reverse('home')), reverse('qr-devices'))


# ---------------------------------------------------------------- lisensa, kolokasaun, daftar staf, notifikasi
import datetime  # noqa: E402

from django.core.cache import cache  # noqa: E402
from django.utils import timezone  # noqa: E402

from custom.models import DG, Department, Division, Position, Section, Status  # noqa: E402
from contract.models import Kolokasaun  # noqa: E402
from employee.models import Employee, EmployeeDivision, EmployeePosition, EmployeeUser  # noqa: E402
from leave.models import Leaves, LeaveType  # noqa: E402


class HrBase(TestCase):
	def setUp(self):
		cache.clear()
		call_command('mdi_setup', verbosity=0)
		Status.objects.create(id=1, name='Ativu')
		self.dg = DG.objects.create(code='DG1', name='DG Satu')
		self.div = Division.objects.create(dg=self.dg, code='D1', name='Divisi Satu')
		self.div2 = Division.objects.create(dg=self.dg, code='D2', name='Divisi Dua')
		self.dep = Department.objects.create(division=self.div, code='P1', name='Dep Satu')
		self.pos1 = Position.objects.create(name='Staf')
		self.pos2 = Position.objects.create(name='Xefe')
		self.lt = LeaveType.objects.create(code='AL', name='Cuti')

	def emp(self, first, last='X', dob=None):
		e = Employee.objects.create(first_name=first, last_name=last, status_id=1, hashed='h' + first, date_of_birth=dob)
		EmployeeDivision.objects.create(employee=e, dg=self.dg, division=self.div)
		EmployeePosition.objects.create(employee=e, position=self.pos1)
		return e

	def user(self, group, emp=None):
		u = User.objects.create_user('u_%s_%s' % (group, User.objects.count()), password='x')
		u.groups.add(Group.objects.get(name=group))
		if emp:
			EmployeeUser.objects.create(employee=emp, user=u)
		return u

	def login(self, group, emp=None):
		self.client.logout()
		u = self.user(group, emp)
		self.client.force_login(u)
		return u


class LeaveFlowTests(HrBase):
	def future(self, n):
		return timezone.localdate() + datetime.timedelta(days=n)

	def request(self, group='staff', start=1, end=2, **extra):
		e = self.emp('Maria')
		self.login(group, e)
		data = {'leave_type': self.lt.pk, 'start_date': self.future(start), 'end_date': self.future(end)}
		data.update(extra)
		return e, self.client.post(reverse('leave-new'), data)

	def test_staff_can_request_leave_and_it_waits_for_approval(self):
		e, r = self.request('staff')
		self.assertRedirects(r, reverse('leave-mine'))
		lv = Leaves.objects.get()
		self.assertEqual((lv.employee, lv.is_active, lv.is_confirm), (e, True, False))
		self.assertContains(self.client.get(reverse('leave-mine')), 'Hein')

	def test_all_request_groups_can_open_the_form(self):
		for g in ('admin', 'staff', 'president', 'hr', 'funsionario', 'employee'):
			self.login(g, self.emp('P' + g))
			self.assertEqual(self.client.get(reverse('leave-new')).status_code, 200, g)

	def test_request_validation(self):
		e = self.emp('Maria')
		self.login('staff', e)
		bad = [{'start_date': self.future(3), 'end_date': self.future(1)},            # akhir sebelum awal
			   {'start_date': self.future(-60), 'end_date': self.future(-59)},        # terlalu lama ke belakang
			   {'start_date': self.future(1), 'end_date': self.future(120)}]          # lebih dari 90 hari
		for b in bad:
			b['leave_type'] = self.lt.pk
			self.assertEqual(self.client.post(reverse('leave-new'), b).status_code, 200)
		self.assertEqual(Leaves.objects.count(), 0)
		ok = {'leave_type': self.lt.pk, 'start_date': self.future(1), 'end_date': self.future(3)}
		self.client.post(reverse('leave-new'), ok)
		self.client.post(reverse('leave-new'), dict(ok, start_date=self.future(2), end_date=self.future(4)))   # tumpang tindih
		self.assertEqual(Leaves.objects.count(), 1)

	def test_unlinked_account_cannot_request(self):
		self.login('staff')
		r = self.client.post(reverse('leave-new'), {'leave_type': self.lt.pk, 'start_date': self.future(1), 'end_date': self.future(2)})
		self.assertEqual(r.status_code, 302)
		self.assertEqual(Leaves.objects.count(), 0)

	def test_only_pdf_is_accepted(self):
		from django.core.files.uploadedfile import SimpleUploadedFile
		e = self.emp('Maria')
		self.login('staff', e)
		base = {'leave_type': self.lt.pk, 'start_date': self.future(1), 'end_date': self.future(2)}
		r = self.client.post(reverse('leave-new'), dict(base, file=SimpleUploadedFile('a.pdf', b'<html>bukan pdf')))
		self.assertEqual(r.status_code, 200)
		self.assertEqual(Leaves.objects.count(), 0)

	def test_president_approves_and_staff_cannot(self):
		e, _ = self.request('staff')
		lv = Leaves.objects.get()
		self.assertEqual(self.client.post(reverse('leave-decide', args=[lv.pk, 'approve'])).status_code, 403)
		self.assertEqual(self.client.get(reverse('leave-all')).status_code, 403)
		self.login('hr')                                                   # hr melihat semua tetapi tidak menyetujui
		self.assertContains(self.client.get(reverse('leave-all')), 'Maria')
		self.assertEqual(self.client.post(reverse('leave-decide', args=[lv.pk, 'approve'])).status_code, 403)
		self.login('president')
		self.assertContains(self.client.get(reverse('leave-all')), 'Aprova')
		self.client.post(reverse('leave-decide', args=[lv.pk, 'approve']))
		lv.refresh_from_db()
		self.assertTrue(lv.is_confirm)

	def test_reject_and_no_double_decision(self):
		self.request('staff')
		lv = Leaves.objects.get()
		self.login('admin')
		self.client.post(reverse('leave-decide', args=[lv.pk, 'reject']))
		self.client.post(reverse('leave-decide', args=[lv.pk, 'approve']))        # sudah diproses
		lv.refresh_from_db()
		self.assertEqual((lv.is_active, lv.is_confirm), (False, False))

	def test_cannot_approve_own_leave_and_decide_requires_post(self):
		e = self.emp('Bos')
		self.login('president', e)
		self.client.post(reverse('leave-new'), {'leave_type': self.lt.pk, 'start_date': self.future(1), 'end_date': self.future(2)})
		lv = Leaves.objects.get()
		self.client.post(reverse('leave-decide', args=[lv.pk, 'approve']))
		lv.refresh_from_db()
		self.assertFalse(lv.is_confirm)
		self.assertEqual(self.client.get(reverse('leave-decide', args=[lv.pk, 'approve'])).status_code, 405)

	def test_cancel_only_own_pending(self):
		e, _ = self.request('staff')
		lv = Leaves.objects.get()
		self.login('staff', self.emp('Lain'))
		self.client.post(reverse('leave-cancel', args=[lv.pk]))               # milik orang lain: 404
		lv.refresh_from_db()
		self.assertTrue(lv.is_active)
		self.client.logout()
		self.client.force_login(EmployeeUser.objects.get(employee=e).user)
		self.client.post(reverse('leave-cancel', args=[lv.pk]))
		lv.refresh_from_db()
		self.assertFalse(lv.is_active)

	def test_approved_leave_is_what_the_scanner_reads(self):
		"""Lisensa yang disetujui membuat scan terbaca sebagai lisensa; yang masih menunggu tidak."""
		from zoneinfo import ZoneInfo
		from attendance import qr_service as svc
		from attendance.models import AttendanceStatus
		from attendance.models_qr import QRCard
		for c, n in (('F', 'Falta'), ('P', 'Presensa'), ('L', 'Lisensa')):
			AttendanceStatus.objects.get_or_create(code=c, name=n)
		day = datetime.date.today() + datetime.timedelta(days=1)
		while day.weekday() > 4:
			day += datetime.timedelta(days=1)
		e, _ = self.request('staff', start=(day - datetime.date.today()).days, end=(day - datetime.date.today()).days)
		card = QRCard.objects.create(employee=e)
		now = datetime.datetime(day.year, day.month, day.day, 8, 0, tzinfo=ZoneInfo('Asia/Dili'))
		self.assertEqual(svc.process_scan(svc.make_payload(card), now=now)['code'], 'in')   # masih menunggu: hadir biasa
		from attendance.models import Attendance
		Attendance.objects.all().delete()
		Leaves.objects.update(is_confirm=True)
		self.assertEqual(svc.process_scan(svc.make_payload(card), now=now + datetime.timedelta(minutes=5))['code'], 'leave')


class PlacementTests(HrBase):
	def post(self, e, **kw):
		d = {'position': self.pos2.pk, 'dg': self.dg.pk, 'division': self.div2.pk, 'start_date': timezone.localdate()}
		d.update(kw)
		return self.client.post(reverse('placement-new', args=[e.pk]), d)

	def test_president_allocates_and_report_data_follows(self):
		e = self.emp('Maria')
		self.login('president')
		r = self.post(e)
		self.assertRedirects(r, reverse('placement-history', args=[e.pk]))
		self.assertEqual(EmployeePosition.objects.get(employee=e).position, self.pos2)
		self.assertEqual(EmployeeDivision.objects.get(employee=e).division, self.div2)
		self.assertEqual(Kolokasaun.objects.filter(employee=e, is_active=True).count(), 1)

	def test_new_placement_closes_the_previous_one(self):
		e = self.emp('Maria')
		self.login('admin')
		d0 = timezone.localdate()
		self.post(e, start_date=d0, position=self.pos1.pk)
		self.post(e, start_date=d0 + datetime.timedelta(days=10))
		old, new = Kolokasaun.objects.order_by('id')
		self.assertFalse(old.is_active)
		self.assertEqual(old.end_date, d0 + datetime.timedelta(days=9))
		self.assertTrue(new.is_active)

	def test_rejects_start_before_last_and_mismatched_hierarchy(self):
		e = self.emp('Maria')
		self.login('admin')
		d0 = timezone.localdate()
		self.post(e, start_date=d0)
		self.post(e, start_date=d0 - datetime.timedelta(days=5))                    # sebelum penempatan terakhir
		other_dg = DG.objects.create(code='X', name='Lain')
		self.post(e, dg=other_dg.pk, start_date=d0 + datetime.timedelta(days=1))   # diresaun bukan milik dg
		self.assertEqual(Kolokasaun.objects.count(), 1)

	def test_staff_and_hr_only_view(self):
		e = self.emp('Maria')
		for g in ('staff', 'hr'):
			self.login(g)
			self.assertEqual(self.client.get(reverse('placement-list')).status_code, 200, g)
			self.assertEqual(self.client.get(reverse('placement-history', args=[e.pk])).status_code, 200, g)
			self.assertEqual(self.client.get(reverse('placement-new', args=[e.pk])).status_code, 403, g)
			self.assertEqual(self.post(e).status_code, 403, g)
		for g in ('funsionario', 'employee'):
			self.login(g)
			self.assertEqual(self.client.get(reverse('placement-list')).status_code, 403, g)
		self.assertEqual(Kolokasaun.objects.count(), 0)


class DirectoryTests(HrBase):
	def test_hr_president_admin_see_staff_list_and_detail(self):
		e = self.emp('Maria', 'Silva')
		self.emp('Jose', 'Costa')
		for g in ('hr', 'president', 'admin'):
			self.login(g)
			r = self.client.get(reverse('staff-list'))
			self.assertContains(r, 'Maria')
			self.assertContains(r, 'Jose')
			self.assertContains(self.client.get(reverse('staff-detail', args=[e.pk])), 'Maria')

	def test_search_and_division_filter(self):
		self.emp('Maria', 'Silva')
		j = self.emp('Jose', 'Costa')
		EmployeeDivision.objects.filter(employee=j).update(division=self.div2)
		self.login('hr')
		self.assertNotContains(self.client.get(reverse('staff-list'), {'q': 'Mari'}), 'Costa')
		r = self.client.get(reverse('staff-list'), {'div': self.div2.pk})
		self.assertContains(r, 'Costa')
		self.assertNotContains(r, 'Silva')

	def test_others_cannot_see_the_directory(self):
		e = self.emp('Maria')
		for g in ('staff', 'funsionario', 'employee'):
			self.login(g)
			self.assertEqual(self.client.get(reverse('staff-list')).status_code, 403, g)
			self.assertEqual(self.client.get(reverse('staff-detail', args=[e.pk])).status_code, 403, g)

	def test_list_query_count_is_constant(self):
		from django.db import connection
		from django.test.utils import CaptureQueriesContext
		for i in range(30):
			self.emp('P%d' % i)
		self.login('hr')
		with CaptureQueriesContext(connection) as c:
			self.client.get(reverse('staff-list'))
		self.assertLess(len(c), 15)


class NotifTests(HrBase):
	def today(self):
		from notif import services
		return services.today()

	def test_birthday_today_in_badge_and_home(self):
		t = self.today()
		self.emp('Ana', 'Lopes', dob=datetime.date(1990, t.month, t.day))
		self.emp('Jose', 'Costa', dob=datetime.date(1990, 1 if t.month != 1 else 2, 15))
		self.login('staff')
		d = self.client.get(reverse('notif-badge')).json()
		self.assertEqual((d['birthdays'], d['names'], d['leaves'], d['value']), (1, ['Ana Lopes'], 0, 1))
		self.assertContains(self.client.get(reverse('home')), 'Ana Lopes')

	def test_badge_counts_pending_leaves_only_for_approvers(self):
		e = self.emp('Maria')
		Leaves.objects.create(employee=e, leave_type=self.lt, start_date=timezone.localdate(), end_date=timezone.localdate(), is_active=True, is_confirm=False)
		self.login('staff')
		self.assertEqual(self.client.get(reverse('notif-badge')).json()['leaves'], 0)
		self.login('president')
		self.assertEqual(self.client.get(reverse('notif-badge')).json()['leaves'], 1)
		self.assertContains(self.client.get(reverse('home')), 'Aprova Lisensa')

	def test_badge_requires_login_and_is_not_cached(self):
		self.client.logout()
		self.assertEqual(self.client.get(reverse('notif-badge')).status_code, 401)
		self.login('staff')
		r = self.client.get(reverse('notif-badge'))
		self.assertEqual(r['Cache-Control'], 'no-store')
		self.assertEqual(self.client.post(reverse('notif-badge')).status_code, 405)

	def test_feb_29_birthday_is_celebrated_on_feb_28_in_normal_years(self):
		from notif import services
		self.emp('Kabisat', 'Z', dob=datetime.date(2000, 2, 29))
		cache.clear()
		self.assertEqual(len(services.birthdays_on(datetime.date(2027, 2, 28))), 1)
		self.assertEqual(len(services.birthdays_on(datetime.date(2028, 2, 28))), 0)
		self.assertEqual(len(services.birthdays_on(datetime.date(2028, 2, 29))), 1)

	def test_birthday_page_lists_the_month_and_survives_bad_input(self):
		self.emp('Ana', 'Lopes', dob=datetime.date(1990, 3, 10))
		self.login('employee')
		self.assertContains(self.client.get(reverse('notif-birthdays'), {'month': 3}), 'Ana Lopes')
		self.assertEqual(self.client.get(reverse('notif-birthdays'), {'month': 'x'}).status_code, 200)
		self.assertEqual(self.client.get(reverse('notif-birthdays'), {'month': 99}).status_code, 200)

	def test_inactive_employee_has_no_birthday_notice(self):
		t = self.today()
		e = self.emp('Pensiun', 'X', dob=datetime.date(1960, t.month, t.day))
		Status.objects.create(id=2, name='Inativu')
		Employee.objects.filter(pk=e.pk).update(status_id=2)
		self.login('staff')
		self.assertEqual(self.client.get(reverse('notif-badge')).json()['birthdays'], 0)


class NavbarRoleTests(HrBase):
	def html(self, group):
		self.login(group, self.emp('E' + group))
		return self.client.get(reverse('home')).content.decode()

	def test_menu_per_role(self):
		matrix = {
			'admin': dict(kiosk=True, cards=True, leave_all=True, place=True, directory=True),
			'president': dict(kiosk=False, cards=False, leave_all=True, place=True, directory=True),
			'hr': dict(kiosk=False, cards=False, leave_all=True, place=True, directory=True),
			'staff': dict(kiosk=False, cards=False, leave_all=False, place=True, directory=False),
			'funsionario': dict(kiosk=False, cards=False, leave_all=False, place=False, directory=False),
		}
		for g, want in matrix.items():
			h = self.html(g)
			self.assertEqual(reverse('qr-devices') in h, want['kiosk'], g)
			self.assertEqual(reverse('qr-cards') in h, want['cards'], g)
			self.assertEqual(reverse('leave-all') in h, want['leave_all'], g)
			self.assertEqual(reverse('placement-list') in h, want['place'], g)
			self.assertEqual(reverse('staff-list') in h, want['directory'], g)
			self.assertIn('notifbadge', h)
			self.assertIn('fa-bell', h)
			self.assertIn('rel="icon"', h)


class EmployeeCrudTests(HrBase):
	def data(self, **kw):
		d = {'first_name': 'Maria', 'last_name': 'Silva', 'date_of_birth': '1990-05-17', 'sex': 'Feto', 'status': 1,
			'nrf': 'NRF-001', 'position': self.pos1.pk, 'dg': self.dg.pk, 'division': self.div.pk,
			'phone': '+670 7712 3456', 'email': 'maria@contoh.org', 'create_account': 'on'}
		d.update(kw)
		return d

	def test_only_admin_can_add_or_edit(self):
		e = self.emp('Maria')
		for g in ('staff', 'president', 'hr', 'funsionario', 'employee'):
			self.login(g)
			self.assertEqual(self.client.get(reverse('employee-add')).status_code, 403, g)
			self.assertEqual(self.client.post(reverse('employee-add'), self.data()).status_code, 403, g)
			self.assertEqual(self.client.get(reverse('employee-edit', args=[e.pk])).status_code, 403, g)
			self.assertEqual(self.client.get(reverse('employee-address', args=[e.pk])).status_code, 403, g)
		self.assertEqual(Employee.objects.count(), 1)

	def test_add_creates_everything_card_and_account_with_random_password(self):
		from attendance.models_qr import QRCard
		from employee.models import ContactInfo, IDFNumber
		self.login('admin')
		r = self.client.post(reverse('employee-add'), self.data(), follow=True)
		e = Employee.objects.get(first_name='Maria')
		self.assertRedirects(r, reverse('staff-detail', args=[e.pk]))
		self.assertEqual(IDFNumber.objects.get(employee=e).nrf, 'NRF-001')
		self.assertEqual(EmployeePosition.objects.get(employee=e).position, self.pos1)
		self.assertEqual(EmployeeDivision.objects.get(employee=e).division, self.div)
		self.assertEqual(ContactInfo.objects.get(employee=e).email, 'maria@contoh.org')
		self.assertTrue(QRCard.objects.filter(employee=e).exists())
		link = EmployeeUser.objects.get(employee=e)
		self.assertEqual(link.user.username, 'NRF-001')
		self.assertTrue(link.user.groups.filter(name='funsionario').exists())
		msgs = [m.message for m in r.context['messages']]
		pwd = [m for m in msgs if 'Password:' in m][0].split('Password: ')[1].split(' ')[0]
		self.assertNotEqual(pwd.lower(), 'password')
		self.assertEqual(len(pwd), 10)
		self.assertTrue(link.user.check_password(pwd))

	def test_validation_blocks_bad_input(self):
		self.login('admin')
		self.client.post(reverse('employee-add'), self.data(nrf='N1'))
		bad = [self.data(nrf='n1'),                                                # NRF ganda (tak peduli huruf besar)
			self.data(nrf='N2', date_of_birth='2999-01-01'),
			self.data(nrf='N3', phone='abc'),
			self.data(nrf='N4', email='bukan-email'),
			self.data(nrf='N5', first_name=''),
			self.data(nrf='N6', division=self.div2.pk, dg=DG.objects.create(code='X', name='Lain').pk)]
		for b in bad:
			self.assertEqual(self.client.post(reverse('employee-add'), b).status_code, 200, b)
		self.assertEqual(Employee.objects.count(), 1)

	def test_username_collision_gets_a_suffix(self):
		User.objects.create_user('NRF-001', password='x')
		self.login('admin')
		self.client.post(reverse('employee-add'), self.data())
		self.assertTrue(User.objects.filter(username='NRF-0012').exists())

	def test_edit_updates_and_does_not_make_a_second_account_or_card(self):
		from attendance.models_qr import QRCard
		self.login('admin')
		self.client.post(reverse('employee-add'), self.data())
		e = Employee.objects.get(first_name='Maria')
		r = self.client.post(reverse('employee-edit', args=[e.pk]), self.data(first_name='Mariana', position=self.pos2.pk))
		self.assertRedirects(r, reverse('staff-detail', args=[e.pk]))
		e.refresh_from_db()
		self.assertEqual(e.first_name, 'Mariana')
		self.assertEqual(EmployeePosition.objects.get(employee=e).position, self.pos2)
		self.assertEqual(EmployeeUser.objects.filter(employee=e).count(), 1)
		self.assertEqual(QRCard.objects.filter(employee=e).count(), 1)
		self.assertEqual(self.client.get(reverse('employee-edit', args=[e.pk])).status_code, 200)

	def test_photo_accepts_only_real_images(self):
		import io
		from django.core.files.uploadedfile import SimpleUploadedFile
		from PIL import Image
		self.login('admin')
		buf = io.BytesIO()
		Image.new('RGB', (20, 20), 'red').save(buf, 'PNG')
		bad = self.client.post(reverse('employee-add'), self.data(nrf='A', image=SimpleUploadedFile('x.png', b'bukan gambar')))
		self.assertEqual(bad.status_code, 200)
		self.assertEqual(Employee.objects.count(), 0)
		import tempfile
		from django.test import override_settings
		with tempfile.TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
			ok = self.client.post(reverse('employee-add'), self.data(nrf='B', image=SimpleUploadedFile('x.png', buf.getvalue(), 'image/png')))
			self.assertEqual(ok.status_code, 302)
			from employee.models import Photo
			self.assertTrue(Photo.objects.get().image.name.startswith('employee_files/'))

	def test_address_chain_is_validated(self):
		from custom.models import AdministrativePost, Municipality, Village
		from employee.models import LocationTL
		m1, m2 = Municipality.objects.create(code='1', name='Dili'), Municipality.objects.create(code='2', name='Baucau')
		p1 = AdministrativePost.objects.create(municipality=m1, name='Nain Feto')
		v1 = Village.objects.create(administrativepost=p1, name='Pite')
		e = self.emp('Maria')
		self.login('admin')
		url = reverse('employee-address', args=[e.pk])
		self.client.post(url, {'municipality': m2.pk, 'administrativepost': p1.pk})          # posto bukan milik municipiu
		self.assertFalse(LocationTL.objects.filter(employee=e).exists())
		self.client.post(url, {'municipality': m1.pk, 'administrativepost': p1.pk, 'village': v1.pk, 'aldeia': 'A1'})
		self.assertEqual(LocationTL.objects.get(employee=e).village, v1)
		self.assertContains(self.client.get(url), 'Pite')                                  # terpilih lagi saat dibuka

	def test_add_button_only_for_admin_in_list(self):
		self.login('admin')
		self.assertContains(self.client.get(reverse('staff-list')), reverse('employee-add'))
		self.login('hr')
		self.assertNotContains(self.client.get(reverse('staff-list')), reverse('employee-add'))


class TopbarTests(HrBase):
	def page(self):
		self.login('staff', self.emp('Tes'))
		return self.client.get(reverse('home')).content.decode()

	def test_topbar_uses_the_active_institute(self):
		from custom.models import Institute, Municipality
		m = Municipality.objects.create(code='01', name='Dili')
		Institute.objects.create(name='Mata Dalan Institute', address='Rua Presidente Nicolau Lobato', municipality=m,
			phone='+670 7700 0000', email='info@mdi.tl', is_active=True)
		cache.clear()
		h = self.page()
		self.assertIn('class="topbar"', h)
		self.assertIn('Rua Presidente Nicolau Lobato, Dili', h)
		self.assertIn('href="tel:+67077000000"', h)
		self.assertIn('href="mailto:info@mdi.tl"', h)

	def test_inactive_institute_and_empty_settings_show_no_contact(self):
		from custom.models import Institute
		Institute.objects.create(name='Lain', phone='123456', email='x@y.tl', is_active=False)
		cache.clear()
		h = self.page()
		self.assertNotIn('tel:', h)
		self.assertNotIn('mailto:', h)
		self.assertIn('class="topbar"', h)

	def test_settings_fallback_and_bad_email_dropped(self):
		from django.test import override_settings
		cache.clear()
		with override_settings(SITE_ADDRESS='Dili', SITE_PHONE='7700', SITE_EMAIL='bukan-email'):
			h = self.page()
		self.assertIn('Dili', h)
		self.assertIn('tel:7700', h)
		self.assertNotIn('mailto:', h)

	def test_contact_values_are_escaped(self):
		from custom.models import Institute
		Institute.objects.create(name='X', address='<script>alert(1)</script>', phone='"><b>1', is_active=True)
		cache.clear()
		h = self.page()
		self.assertNotIn('<script>alert(1)</script>', h)
		self.assertNotIn('href="tel:"><b>', h)

	def test_flags_are_at_the_far_right_of_the_navbar(self):
		h = self.page()
		self.assertGreater(h.index('qr-flags'), h.index('id="profile"'))      # setelah menu profil = paling kanan
		self.assertEqual(h.count('class="qr-flag"') + h.count('class="qr-flag on"'), 4)
		self.assertLess(h.index('class="topbar"'), h.index('<header class="site-header">'))
