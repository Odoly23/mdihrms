from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from attendance.models import AttendanceStatus


class ProjectTests(TestCase):
	def test_setup_command_is_idempotent(self):
		call_command('mdi_setup', verbosity=0)
		call_command('mdi_setup', verbosity=0)
		self.assertEqual(Group.objects.count(), 5)
		self.assertEqual(list(AttendanceStatus.objects.order_by('id').values_list('code', flat=True)), ['F', 'P', 'L'])

	def test_login_required_and_login_page(self):
		self.assertEqual(self.client.get(reverse('home')).status_code, 302)
		self.assertContains(self.client.get(reverse('login')), 'MDI-HRMS')

	def test_home_for_each_group_and_without_group(self):
		call_command('mdi_setup', verbosity=0)
		for name in ('admin', 'staff', 'president', 'funsionario', 'employee', None):
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
