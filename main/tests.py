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
			self.assertContains(r, 'main-navbar')

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

	def test_flags_are_in_the_topbar_not_the_navbar(self):
		h = self.page()
		bar, nav = h.index('class="topbar"'), h.index('<header class="site-header">')
		self.assertEqual(h.count('class="qr-flag"') + h.count('class="qr-flag on"'), 4)
		self.assertTrue(bar < h.index('qr-flags') < nav)                        # semua bendera di dalam topbar
		self.assertEqual(h.count('qr-flags'), 1)
		for code in ('tet', 'en', 'id', 'pt'):
			self.assertIn('/attendance/qr/lang/%s/?next=' % code, h)


class FullTranslationTests(HrBase):
	"""Satu klik bendera mengganti SELURUH tampilan: tidak ada teks Tetun yang tersisa di bahasa lain."""
	LANGS = ('en', 'id', 'pt')
	TETUN_ONLY = ('Husu lisensa', 'Lisensa hotu', 'Ha\'u nia lisensa', 'Hela fatin', 'Kolokasaun foun', 'Laiha dadus',
		'Haree hotu', 'ANIVERSÁRIU OHIN', 'Funsionáriu', 'Rezumu', 'VARANDA', 'FUNSIONÁRIU')

	def pages(self, emp):
		return [reverse('home'), reverse('leave-mine'), reverse('leave-new'), reverse('leave-all'), reverse('placement-list'),
			reverse('placement-history', args=[emp.pk]), reverse('placement-new', args=[emp.pk]), reverse('staff-list'),
			reverse('staff-detail', args=[emp.pk]), reverse('employee-add'), reverse('employee-edit', args=[emp.pk]),
			reverse('employee-address', args=[emp.pk]), reverse('notif-birthdays')]

	def test_no_tetun_left_over_in_other_languages(self):
		e = self.emp('Maria')
		self.login('admin', self.emp('Admin'))
		for lang in self.LANGS:
			self.client.cookies['mdi_lang'] = lang
			for url in self.pages(e):
				r = self.client.get(url)
				self.assertEqual(r.status_code, 200, (lang, url))
				html = r.content.decode()
				self.assertIn('<html lang="%s">' % lang, html)
				body = html[html.index('class="topbar"'):]
				for word in self.TETUN_ONLY:
					self.assertNotIn('>' + word, body.replace('> ', '>'), (lang, url, word))

	def test_each_language_shows_its_own_texts(self):
		self.login('admin', self.emp('Admin'))
		want = {'tet': 'Husu lisensa', 'en': 'Request leave', 'id': 'Ajukan cuti', 'pt': 'Pedir licença'}
		for lang, text in want.items():
			self.client.cookies['mdi_lang'] = lang
			self.assertContains(self.client.get(reverse('leave-new')), text)

	def test_form_labels_choices_and_errors_follow_the_language(self):
		self.login('admin')
		self.client.cookies['mdi_lang'] = 'en'
		h = self.client.get(reverse('employee-add')).content.decode()
		for text in ('First name', 'Date of birth', 'Male', 'Married', 'Create login account'):
			self.assertIn(text, h)
		r = self.client.post(reverse('employee-add'), {'first_name': 'X', 'date_of_birth': '2999-01-01', 'status': 1})
		self.assertContains(r, 'The date of birth is not valid.')
		self.client.cookies['mdi_lang'] = 'pt'
		self.assertContains(self.client.post(reverse('employee-add'), {'first_name': 'X', 'date_of_birth': '2999-01-01', 'status': 1}),
			'A data de nascimento não é válida.')

	def test_flash_messages_follow_the_language(self):
		e = self.emp('Maria')
		self.login('staff', e)
		self.client.cookies['mdi_lang'] = 'id'
		r = self.client.post(reverse('leave-new'), {'leave_type': self.lt.pk,
			'start_date': timezone.localdate() + datetime.timedelta(days=1), 'end_date': timezone.localdate() + datetime.timedelta(days=2)}, follow=True)
		self.assertContains(r, 'Pengajuan cuti terkirim')
		self.assertContains(r, 'Menunggu')

	def test_birthday_page_uses_translated_month_names(self):
		self.login('staff')
		self.client.cookies['mdi_lang'] = 'pt'
		self.assertContains(self.client.get(reverse('notif-birthdays'), {'month': 3}), 'Março')

	def test_login_and_error_pages_translate_and_have_flags(self):
		self.client.logout()
		self.client.cookies['mdi_lang'] = 'en'
		r = self.client.get(reverse('login'))
		self.assertContains(r, 'Log in')
		self.assertContains(r, '/attendance/qr/lang/pt/')
		r = self.client.get('/tidak-ada/')
		self.assertEqual(r.status_code, 404)
		self.assertContains(r, 'Page not found.', status_code=404)

	def test_language_switch_works_without_login_and_returns_to_page(self):
		self.client.logout()
		r = self.client.get(reverse('qr-lang', args=['pt']) + '?next=/login/')
		self.assertRedirects(r, '/login/', fetch_redirect_response=False)
		self.assertEqual(r.cookies['mdi_lang'].value, 'pt')


class ShellLayoutTests(HrBase):
	def html(self, group='staff'):
		self.login(group, self.emp('E' + group))
		return self.client.get(reverse('home')).content.decode()

	def test_structure_topbar_navbar_offcanvas(self):
		h = self.html('admin')
		order = [h.index(x) for x in ('class="topbar"', 'class="main-navbar"', 'id="sidebar"', 'id="overlay"', 'role="main"', 'class="page-footer font-small site-footer"')]
		self.assertEqual(order, sorted(order))
		self.assertIn('id="btnHam"', h)
		self.assertIn('aria-controls="sidebar"', h)
		self.assertIn('offcanvas.js', h)
		self.assertIn('class="brand"', h)

	def test_sidebar_items_follow_the_role(self):
		def side(group):
			h = self.html(group)
			return h[h.index('id="sidebar"'):h.index('id="overlay"')]
		adm, stf, fun = side('admin'), side('staff'), side('funsionario')
		self.assertIn(reverse('qr-devices'), adm)
		self.assertIn(reverse('qr-cards'), adm)
		self.assertNotIn(reverse('qr-devices'), stf)
		self.assertNotIn(reverse('qr-cards'), stf)
		self.assertIn(reverse('qr-today'), stf)
		self.assertNotIn(reverse('qr-today'), fun)
		self.assertNotIn(reverse('staff-list'), fun)
		for s in (adm, stf, fun):
			self.assertIn('action="%s"' % reverse('logout'), s)              # keluar lewat POST

	def test_colour_comes_from_one_variable_and_sample_values(self):
		import os
		from django.conf import settings
		css = open(os.path.join(settings.BASE_DIR, 'main/static/main/css/main.css')).read()
		for needle in ('--navy: #e3171e', '--topbar-h: 34px', '--navbar-h: 62px', '--header-h: 96px', '--sb-w: 72px',
				'.topbar', '.main-navbar', '.nav-links', '.btn-ham', '#sidebar', '#overlay', '.sb-body', '.sb-sec', 'body.sb-open footer'):
			self.assertIn(needle, css, needle)

	def test_full_meta_tags_container_and_favicon(self):
		h = self.html('admin')
		for needle in ('<meta charset="utf-8">', 'name="viewport"', 'name="description"', 'name="theme-color" content="#e3171e"',
				'name="robots"', 'rel="apple-touch-icon"', 'favicon.ico', '<title>MDI-HRMS - ', '<html lang="tet">'):
			self.assertIn(needle, h, needle)
		self.assertIn('<main role="main" class="container page-wrapper">', h)
		self.assertIn('<div class="row">', h[h.index('role="main"'):])
		self.assertIn('col-md-12', h)
		self.assertNotIn('#00B050', h)

	def test_logo_colours_in_css_and_icons_exist(self):
		import os
		from django.conf import settings
		base = os.path.join(settings.BASE_DIR, 'main/static/main')
		for f in ('images/favicon.ico', 'images/favicon.jpg', 'images/apple-touch-icon.png'):
			self.assertTrue(os.path.getsize(os.path.join(base, f)) > 500, f)
		css = open(os.path.join(base, 'css/main.css')).read()
		self.assertIn('--navy-dk: #a80f14', css)
		self.assertNotIn('00B050', css)

	def test_logo_red_only_in_theme_meta_not_inline_styles(self):
		h = self.html('admin')
		self.assertEqual(h.count('#e3171e'), 1)                                  # hanya <meta name="theme-color">


class AttendanceConfigTests(HrBase):
	def setUp(self):
		super().setUp()
		from attendance.models import AttendanceStatus, Month, Year
		Year.objects.all().delete(); Month.objects.all().delete()                   # buang isian mdi_setup agar tes deterministik
		self.y25, self.y26 = Year.objects.create(year=2025), Year.objects.create(year=2026, is_active=True)
		self.m = [Month.objects.create(code=i, name='M%d' % i, is_active=(i == 11)) for i in (10, 11, 12)]
		for c, n in (('F', 'Falta'), ('P', 'Presensa'), ('L', 'Lisensa')):
			AttendanceStatus.objects.get_or_create(code=c, defaults={'name': n})

	def test_only_admin_can_open_any_config_page(self):
		urls = [reverse('attendance-custom-dash'), reverse('attendance-custom-holiday-list'), reverse('attendance-custom-holiday-add'),
			reverse('attendance-custom-tolerance-list'), reverse('attendance-custom-tolerance-add'), reverse('attendance-custom-status-add')]
		for g in ('staff', 'president', 'hr', 'funsionario', 'employee'):
			self.login(g)
			for u in urls:
				self.assertEqual(self.client.get(u).status_code, 403, (g, u))
			self.assertEqual(self.client.post(reverse('attendance-custom-year', args=[self.y25.pk])).status_code, 403, g)
		self.login('admin')
		for u in urls:
			self.assertEqual(self.client.get(u).status_code, 200, u)

	def test_dash_has_year_month_status_like_the_old_page(self):
		self.login('admin')
		h = self.client.get(reverse('attendance-custom-dash')).content.decode()
		for text in ('Ativa tinan', 'Ativa fulan', 'STATUS ABSENSIA', '2025', '2026', 'Novembru', 'Falta'):
			self.assertIn(text, h)
		self.assertIn('fa fa-check', h)
		self.assertIn('fa-lock', h)                                          # sigla F/P/L terkunci

	def test_activating_a_year_or_month_is_post_only_and_exclusive(self):
		self.login('admin')
		self.assertEqual(self.client.get(reverse('attendance-custom-year', args=[self.y25.pk])).status_code, 405)
		self.client.post(reverse('attendance-custom-year', args=[self.y25.pk]))
		self.y25.refresh_from_db(); self.y26.refresh_from_db()
		self.assertEqual((self.y25.is_active, self.y26.is_active), (True, False))
		self.assertEqual(self.client.get(reverse('attendance-custom-month', args=[self.m[0].pk])).status_code, 405)
		self.client.post(reverse('attendance-custom-month', args=[self.m[0].pk]))
		from attendance.models import Month
		self.assertEqual(list(Month.objects.filter(is_active=True).values_list('code', flat=True)), [10])
		self.assertEqual(self.client.post(reverse('attendance-custom-year', args=[99999])).status_code, 404)

	def test_add_year_validation(self):
		from attendance.models import Year
		self.login('admin')
		self.client.post(reverse('attendance-custom-year-add'), {'year': 2027})
		self.assertTrue(Year.objects.filter(year=2027).exists())
		for bad in ('2027', '1999', '2101', 'abc', ''):
			self.client.post(reverse('attendance-custom-year-add'), {'year': bad})
		self.assertEqual(Year.objects.filter(year=2027).count(), 1)
		self.assertEqual(Year.objects.count(), 3)

	def test_status_codes_used_by_qr_are_protected(self):
		from attendance.models import AttendanceStatus
		self.login('admin')
		p = AttendanceStatus.objects.get(code='P')
		r = self.client.post(reverse('attendance-custom-status-update', args=[p.pk]), {'code': 'X', 'name': 'Hadir'})
		p.refresh_from_db()
		self.assertEqual((p.code, p.name), ('P', 'Hadir'))                   # nama boleh diubah, sigla tidak
		self.client.post(reverse('attendance-custom-status-add'), {'code': 'p', 'name': 'Palsu'})   # meniru sigla terkunci
		self.client.post(reverse('attendance-custom-status-add'), {'code': 'S', 'name': 'Sakit'})
		self.client.post(reverse('attendance-custom-status-add'), {'code': 's', 'name': 'Ganda'})
		self.assertEqual(list(AttendanceStatus.objects.filter(code__in=['p', 'S', 's']).values_list('code', flat=True)), ['S'])

	def test_holiday_crud_and_scan_cache_is_dropped(self):
		from attendance import qr_service as svc
		from attendance.models import NacionalHoliday
		self.login('admin')
		cache.set('attqr:hol', {'stale': 1}, 600)
		self.client.post(reverse('attendance-custom-holiday-add'), {'name': 'Kemerdekaan', 'date': '2026-11-28', 'is_active': 'on', 'recurring': 'on'})
		h = NacionalHoliday.objects.get()
		self.assertIsNone(cache.get('attqr:hol'))
		self.assertEqual(svc.holiday_map()[(11, 28)][0], 'holiday')
		self.client.post(reverse('attendance-custom-holiday-add'), {'name': 'Ganda', 'date': '2026-11-28', 'recurring': 'on'})   # tanggal sama
		self.assertEqual(NacionalHoliday.objects.count(), 1)
		self.client.post(reverse('attendance-custom-holiday-update', args=[h.pk]), {'name': 'Kemerdekaan', 'date': '2026-11-28', 'recurring': 'on'})  # nonaktif
		h.refresh_from_db()
		self.assertFalse(h.is_active)
		self.assertNotIn((11, 28), svc.holiday_map())
		self.assertContains(self.client.get(reverse('attendance-custom-holiday-list')), 'Kemerdekaan')

	def test_tolerance_recurs_every_year_like_a_holiday(self):
		from attendance import qr_service as svc
		from attendance.models import Tolerance, Year
		self.login('admin')
		self.client.post(reverse('attendance-custom-tolerance-add'), {'name': 'Natal', 'date': '2026-12-24', 'is_active': 'on', 'recurring': 'on'})
		t = Tolerance.objects.get()
		self.assertEqual(t.year, self.y26)                                       # kolom tahun lama: ikut tahun pada tanggal
		hol = svc.holiday_map()
		self.assertEqual(hol[(12, 24)], ('tolerance', 'Natal'))                  # berlaku untuk 24 Des tahun berapa pun
		for year in (2026, 2027, 2030):
			self.assertEqual(svc.holiday_map().get(datetime.date(year, 12, 24).timetuple()[1:3])[0], 'tolerance')
		self.assertContains(self.client.get(reverse('attendance-custom-tolerance-list')), 'Natal')
		self.client.post(reverse('attendance-custom-year', args=[self.y25.pk]))        # tahun aktif berubah: daftar tetap sama
		h = self.client.get(reverse('attendance-custom-tolerance-list')).content.decode()
		self.assertIn('Natal', h)
		self.assertIn('24 de Dezembru', h)
		self.assertIn('Kada tinan', h)

	def test_tolerance_needs_no_active_year_and_creates_the_year_row(self):
		from attendance.models import Tolerance, Year
		self.login('admin')
		Year.objects.update(is_active=False)
		self.client.post(reverse('attendance-custom-tolerance-add'), {'name': 'Pontu', 'date': '2028-02-29', 'recurring': 'on'})
		self.assertEqual(Tolerance.objects.get().year.year, 2028)

	def test_same_day_and_month_cannot_repeat_in_another_year(self):
		from attendance.models import NacionalHoliday, Tolerance
		self.login('admin')
		self.client.post(reverse('attendance-custom-tolerance-add'), {'name': 'A', 'date': '2026-12-24', 'is_active': 'on', 'recurring': 'on'})
		self.client.post(reverse('attendance-custom-tolerance-add'), {'name': 'B', 'date': '2027-12-24', 'is_active': 'on', 'recurring': 'on'})
		self.assertEqual(Tolerance.objects.count(), 1)
		self.client.post(reverse('attendance-custom-holiday-add'), {'name': 'X', 'date': '1999-11-12', 'is_active': 'on', 'recurring': 'on'})
		self.client.post(reverse('attendance-custom-holiday-add'), {'name': 'Y', 'date': '2026-11-12', 'is_active': 'on', 'recurring': 'on'})
		self.assertEqual(NacionalHoliday.objects.count(), 1)

	def test_tolerance_day_is_announced_like_a_holiday_every_year(self):
		from attendance import holidays
		from attendance.models import Tolerance
		Tolerance.objects.create(year=self.y26, name='Tolerânsia Natal', date=datetime.date(2026, 12, 24), is_active=True)
		for day in (datetime.date(2026, 12, 23), datetime.date(2027, 12, 23)):         # 24 Des 2026 = Kamis, 24 Des 2027 = Jumat
			n = holidays.notice(day, 'tet')
			self.assertIn('Tolerânsia Natal', n['text'])
			self.assertIn('de Dezembru %d' % (day.year), n['text'])

	def test_translated_in_four_languages(self):
		self.login('admin')
		want = {'tet': 'Ativa tinan', 'en': 'Active year', 'id': 'Tahun aktif', 'pt': 'Ano ativo'}
		for lang, text in want.items():
			self.client.cookies['mdi_lang'] = lang
			self.assertContains(self.client.get(reverse('attendance-custom-dash')), text)
		self.client.cookies['mdi_lang'] = 'en'
		self.assertContains(self.client.get(reverse('attendance-custom-dash')), 'November')
		r = self.client.post(reverse('attendance-custom-year-add'), {'year': 1900}, follow=True)
		self.assertContains(r, 'The year must be between 2000 and 2100.')

	def test_setup_command_seeds_months_and_years(self):
		from attendance.models import Month, Year
		Month.objects.all().delete(); Year.objects.all().delete()
		call_command('mdi_setup', verbosity=0)
		call_command('mdi_setup', verbosity=0)
		self.assertEqual(Month.objects.count(), 12)
		self.assertEqual(Year.objects.count(), 3)
		self.assertEqual(Month.objects.filter(is_active=True).count(), 1)
		self.assertEqual(Year.objects.filter(is_active=True).count(), 1)
		self.assertEqual(Month.objects.get(code=1).name, 'Janeiru')

	def test_menu_links_for_admin_only(self):
		self.login('admin', self.emp('A'))
		self.assertContains(self.client.get(reverse('home')), reverse('attendance-custom-dash'))
		self.login('hr', self.emp('H'))
		self.assertNotContains(self.client.get(reverse('home')), reverse('attendance-custom-dash'))


class HolidayNoticeTests(HrBase):
	"""12 de Novembru (Masacre Santa Cruz) berulang tiap tahun; semua orang diberi tahu hari sebelumnya."""

	def at(self, y, m, d, hh=10):
		import datetime as dt
		from zoneinfo import ZoneInfo
		return dt.datetime(y, m, d, hh, 0, tzinfo=ZoneInfo('Asia/Dili'))

	def setUp(self):
		super().setUp()
		from attendance.models import NacionalHoliday
		NacionalHoliday.objects.create(name='Masacre Santa Cruz', date=datetime.date(1999, 11, 12), is_active=True)

	def page(self, y, m, d, group='funsionario', lang=None, url='home'):
		from unittest import mock
		self.login(group, self.emp('E%s' % group))
		if lang:
			self.client.cookies['mdi_lang'] = lang
		with mock.patch.object(timezone, 'now', lambda: self.at(y, m, d)):
			return self.client.get(reverse(url)).content.decode()

	def test_full_date_formats(self):
		from attendance import qr_i18n as i18n
		d = datetime.date(2026, 11, 12)                                        # Kamis
		self.assertEqual(i18n.fmt_full(d, 'tet'), 'Kinta, 12 de Novembru 2026')
		self.assertEqual(i18n.fmt_full(d, 'pt', weekday=False), '12 de Novembro 2026')
		self.assertEqual(i18n.fmt_full(d, 'en'), 'Thursday, 12 November 2026')
		self.assertEqual(i18n.fmt_full(d, 'id'), 'Kamis, 12 November 2026')

	def test_everyone_sees_tomorrows_holiday_banner_in_each_language(self):
		want = {'tet': 'Aban, Kinta, 12 de Novembru 2026, feriadu: Masacre Santa Cruz',
			'en': 'Tomorrow, Thursday, 12 November 2026, is a holiday: Masacre Santa Cruz',
			'id': 'Besok, Kamis, 12 November 2026, libur: Masacre Santa Cruz',
			'pt': 'Amanhã, Quinta-feira, 12 de Novembro 2026, é feriado: Masacre Santa Cruz'}
		for g in ('funsionario', 'staff', 'president', 'hr', 'admin'):
			for lang, text in want.items():
				h = self.page(2026, 11, 11, g, lang)
				self.assertIn('class="holiday-banner"', h, (g, lang))
				self.assertIn(text, h, (g, lang))

	def test_banner_today_then_gone(self):
		self.assertIn('is-today', self.page(2026, 11, 12))
		self.assertIn('Ohin, Kinta, 12 de Novembru 2026', self.page(2026, 11, 12))
		self.assertNotIn('holiday-banner', self.page(2026, 11, 13))
		self.assertNotIn('holiday-banner', self.page(2026, 11, 10))           # dua hari sebelumnya: belum

	def test_recurs_every_year_but_only_on_weekdays(self):
		from attendance import holidays
		n27 = holidays.notice(datetime.date(2027, 11, 11), 'tet')               # 12 Nov 2027 = Jumat
		self.assertIn('Sexta, 12 de Novembru 2027', n27['text'])
		self.assertIn('Masacre Santa Cruz', n27['text'])
		self.assertIsNone(holidays.notice(datetime.date(2028, 11, 11), 'tet'))  # 12 Nov 2028 = Minggu: libur toh sudah
		self.assertEqual(holidays.upcoming(datetime.date(2028, 11, 1), days=30)[0]['weekend'], True)   # tetap tampil di daftar

	def test_no_banner_for_anonymous_or_inactive_holiday(self):
		from attendance.models import NacionalHoliday
		self.client.logout()
		self.assertNotIn('holiday-banner', self.client.get(reverse('login')).content.decode())
		NacionalHoliday.objects.update(is_active=False)
		cache.clear()
		self.assertNotIn('holiday-banner', self.page(2026, 11, 11))

	def test_home_card_lists_upcoming_holidays_with_days_left(self):
		h = self.page(2026, 11, 5)
		self.assertIn('FERIADU BESIK', h)
		self.assertIn('Kinta, 12 de Novembru 2026', h)
		self.assertIn('Iha loron 7', h)
		self.assertIn('Aban', self.page(2026, 11, 11))
		self.assertIn('Laiha feriadu iha loron 90 oin mai.', self.page(2026, 11, 13))

	def test_config_list_shows_every_year_event_year_and_next_date(self):
		from unittest import mock
		self.login('admin')
		with mock.patch.object(timezone, 'now', lambda: self.at(2026, 11, 11)):
			h = self.client.get(reverse('attendance-custom-holiday-list')).content.decode()
		for text in ('12 de Novembru', '1999', 'Kinta, 12 de Novembru 2026', 'Masacre Santa Cruz', 'Kada tinan', 'Tinan referénsia'):
			self.assertIn(text, h)

	def test_holiday_accepts_event_year_but_tolerance_does_not(self):
		from attendance.models import NacionalHoliday, Tolerance, Year
		self.login('admin')
		self.client.post(reverse('attendance-custom-holiday-add'), {'name': 'Kemerdekaan', 'date': '1975-11-28', 'is_active': 'on', 'recurring': 'on'})
		self.assertTrue(NacionalHoliday.objects.filter(date=datetime.date(1975, 11, 28)).exists())
		self.client.post(reverse('attendance-custom-holiday-add'), {'name': 'Salah', 'date': '1899-01-01'})
		self.assertFalse(NacionalHoliday.objects.filter(name='Salah').exists())
		Year.objects.create(year=2026, is_active=True)
		self.client.post(reverse('attendance-custom-tolerance-add'), {'name': 'Lama', 'date': '1999-12-24', 'recurring': 'on'})
		self.assertFalse(Tolerance.objects.exists())

	def test_next_occurrence_helper(self):
		from attendance.holidays import next_occurrence
		d = datetime.date(1999, 11, 12)
		self.assertEqual(next_occurrence(d, datetime.date(2026, 11, 12)), datetime.date(2026, 11, 12))       # hari ini dihitung
		self.assertEqual(next_occurrence(d, datetime.date(2026, 11, 13)), datetime.date(2027, 11, 12))
		leap = datetime.date(2000, 2, 29)
		self.assertEqual(next_occurrence(leap, datetime.date(2027, 1, 1)), datetime.date(2027, 2, 28))
		self.assertEqual(next_occurrence(leap, datetime.date(2028, 1, 1)), datetime.date(2028, 2, 29))


class RecurringFlagTests(HrBase):
	"""Berulang tiap tahun (bawaan) atau hanya tanggal persis; aturan duplikat mengikuti itu."""

	def post(self, d, recurring, name='X'):
		data = {'name': name, 'date': d, 'is_active': 'on'}
		if recurring:
			data['recurring'] = 'on'
		return self.client.post(reverse('attendance-custom-holiday-add'), data)

	def test_once_only_holiday_can_be_added_and_is_labelled(self):
		from attendance.models import NacionalHoliday
		self.login('admin')
		self.post('2026-04-03', False, 'Sexta Santa')
		self.assertFalse(NacionalHoliday.objects.get().recurring)
		self.assertIn('Dala ida deit', self.client.get(reverse('attendance-custom-holiday-list')).content.decode())

	def test_the_form_checkbox_defaults_to_recurring(self):
		self.login('admin')
		h = self.client.get(reverse('attendance-custom-holiday-add')).content.decode()
		self.assertRegex(h, r'name="recurring"[^>]*checked')

	def test_duplicate_rules_depend_on_recurrence(self):
		from attendance.models import NacionalHoliday
		self.login('admin')
		self.post('2026-04-03', False)
		self.post('2026-04-03', False)                       # tanggal persis ganda: ditolak
		self.post('2027-04-03', False)                       # tahun lain: boleh karena bukan berulang
		self.assertEqual(NacionalHoliday.objects.count(), 2)
		self.post('2000-05-20', True)
		self.post('2000-05-20', True)                        # berulang ganda: ditolak
		self.post('2026-05-20', False)                       # sudah tercakup yang berulang: ditolak
		self.assertEqual(NacionalHoliday.objects.filter(date__month=5, date__day=20).count(), 1)


class ToleranceFromHolidayTests(HrBase):
	"""Tombol '+ Tolerânsia' di baris feriadu: formulir tolerânsia terisi nama dan tanggal; admin menyesuaikan harinya."""

	def setUp(self):
		super().setUp()
		from attendance.models import NacionalHoliday
		self.h = NacionalHoliday.objects.create(name='Natal', date=datetime.date(2000, 12, 25), recurring=True)

	def test_holiday_row_links_to_prefilled_tolerance_form(self):
		from unittest import mock
		self.login('admin')
		with mock.patch.object(timezone, 'now', lambda: datetime.datetime(2026, 11, 11, 10, tzinfo=datetime.timezone.utc)):
			page = self.client.get(reverse('attendance-custom-holiday-list')).content.decode()
			self.assertIn('%s?from=%d' % (reverse('attendance-custom-tolerance-add'), self.h.pk), page)
			form = self.client.get(reverse('attendance-custom-tolerance-add'), {'from': self.h.pk}).content.decode()
		self.assertIn('value="Tolerânsia Natal"', form)
		self.assertIn('value="2026-12-25"', form)

	def test_bad_or_missing_source_gives_an_empty_form(self):
		self.login('admin')
		for src in ('x', '99999', '', '-1', '99999999999999999999'):
			r = self.client.get(reverse('attendance-custom-tolerance-add'), {'from': src})
			self.assertEqual(r.status_code, 200, src)
			self.assertNotIn('Tolerânsia Natal', r.content.decode(), src)

	def test_saving_still_validates_and_creates_the_year(self):
		from attendance.models import Tolerance
		self.login('admin')
		self.client.post(reverse('attendance-custom-tolerance-add'), {'name': 'Tolerânsia Natal', 'date': '2026-12-24', 'is_active': 'on', 'recurring': 'on'})
		self.assertEqual(Tolerance.objects.get().year.year, 2026)

	def test_only_admin_sees_the_prefill_route(self):
		self.login('hr')
		self.assertEqual(self.client.get(reverse('attendance-custom-tolerance-add'), {'from': self.h.pk}).status_code, 403)
