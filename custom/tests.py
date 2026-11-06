from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from custom.models import AdministrativePost, Municipality, Village


class DropdownTests(TestCase):
	def setUp(self):
		self.m1 = Municipality.objects.create(code='01', name='Dili')
		self.m2 = Municipality.objects.create(code='02', name='Baucau')
		self.p1 = AdministrativePost.objects.create(municipality=self.m1, name='Nain Feto')
		self.p0 = AdministrativePost.objects.create(municipality=self.m1, name='Cristo Rei')
		AdministrativePost.objects.create(municipality=self.m2, name='Venilale')
		self.v = Village.objects.create(administrativepost=self.p1, name='Bairro Pite')

	def test_requires_login(self):
		self.assertEqual(self.client.get(reverse('ajax_load_post'), {'municipality': self.m1.pk}).status_code, 302)
		self.assertEqual(self.client.get(reverse('ajax_load_village'), {'administrativepost': self.p1.pk}).status_code, 302)

	def test_posts_of_one_municipality_sorted_by_name(self):
		self.client.force_login(User.objects.create_user('u', password='x'))
		html = self.client.get(reverse('ajax_load_post'), {'municipality': self.m1.pk}).content.decode()
		self.assertIn('---------', html)
		self.assertLess(html.index('Cristo Rei'), html.index('Nain Feto'))
		self.assertNotIn('Venilale', html)

	def test_villages_of_one_post(self):
		self.client.force_login(User.objects.create_user('u', password='x'))
		self.assertIn('Bairro Pite', self.client.get(reverse('ajax_load_village'), {'administrativepost': self.p1.pk}).content.decode())
		self.assertNotIn('Bairro Pite', self.client.get(reverse('ajax_load_village'), {'administrativepost': self.p0.pk}).content.decode())

	def test_missing_or_bad_parameter_returns_only_the_blank_option(self):
		self.client.force_login(User.objects.create_user('u', password='x'))
		for params in ({}, {'municipality': ''}, {'municipality': 'x'}, {'municipality': '99999999999999999999'}):
			r = self.client.get(reverse('ajax_load_post'), params)
			self.assertEqual(r.status_code, 200)
			self.assertNotIn('<option value="1"', r.content.decode())
