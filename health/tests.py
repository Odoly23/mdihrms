import datetime
import os
import shutil
import tempfile
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from leave.models import Leaves
from main.tests import HrBase

from . import services
from .models import HealthClaim

PDF = b'%PDF-1.4\n%fake but valid header\n'
PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 20
JPG = b'\xff\xd8\xff\xe0' + b'\x00' * 20


class HealthBase(HrBase):
	def setUp(self):
		super().setUp()
		self.tmp = tempfile.mkdtemp()
		self.addCleanup(shutil.rmtree, self.tmp, True)
		self._ov = override_settings(MEDIA_ROOT=self.tmp)
		self._ov.enable()
		self.addCleanup(self._ov.disable)
		self.maria = self.emp('Maria', 'Silva')
		self.boss = self.emp('Bos', 'Besar')

	def today(self):
		return timezone.localdate()

	def data(self, **kw):
		d = {'claim_date': (self.today() - datetime.timedelta(days=3)).isoformat(), 'description': 'Konsultasi', 'amount': '45.50',
			'receipt': SimpleUploadedFile('resibu.pdf', PDF, 'application/pdf')}
		d.update(kw)
		return d

	def submit(self, **kw):
		return self.client.post(reverse('health-new'), self.data(**kw))

	def claim(self, employee=None, amount='100', status='pending', **kw):
		c = HealthClaim(employee=employee or self.maria, claim_date=kw.pop('claim_date', self.today()), amount=Decimal(amount), status=status,
			receipt=SimpleUploadedFile('r.pdf', PDF), **kw)
		c.save()
		return c


class RequestTests(HealthBase):
	def test_staff_can_request_and_it_waits_for_approval(self):
		self.login('staff', self.maria)
		r = self.submit()
		self.assertRedirects(r, reverse('health-mine'))
		c = HealthClaim.objects.get()
		self.assertEqual((c.employee, c.status, c.amount, c.approved_amount), (self.maria, 'pending', Decimal('45.50'), None))
		self.assertContains(self.client.get(reverse('health-mine')), 'Hein')

	def test_all_groups_can_open_the_form_but_need_a_linked_employee(self):
		for g in ('admin', 'staff', 'president', 'hr', 'logistik', 'funsionario', 'employee'):
			self.login(g, self.emp('P' + g))
			self.assertEqual(self.client.get(reverse('health-new')).status_code, 200, g)
		self.login('staff')                                                       # akun tanpa pegawai tertaut
		self.assertEqual(self.client.post(reverse('health-new'), self.data()).status_code, 302)
		self.assertEqual(HealthClaim.objects.count(), 0)

	def test_validation(self):
		self.login('staff', self.maria)
		d = self.today()
		bad = [dict(claim_date=(d + datetime.timedelta(days=1)).isoformat()),                    # masa depan
			dict(claim_date=(d - datetime.timedelta(days=200)).isoformat()),                     # terlalu lama
			dict(amount='0'), dict(amount='-5'), dict(amount='abc'), dict(amount='99999999'),
			dict(receipt=SimpleUploadedFile('a.exe', b'MZ' + b'\x00' * 20)),                     # tipe salah
			dict(receipt=SimpleUploadedFile('a.pdf', b'<html>bukan pdf</html>')),                # isi bukan PDF
			dict(receipt=SimpleUploadedFile('a.png', PDF)),                                      # ekstensi tidak cocok dengan isi
			dict(receipt=SimpleUploadedFile('a.pdf', PDF + b'0' * (5 * 1024 * 1024 + 1)))]       # > 5 MB
		for b in bad:
			self.assertEqual(self.submit(**b).status_code, 200, list(b))
		self.assertEqual(HealthClaim.objects.count(), 0)

	def test_image_receipts_are_accepted_and_names_are_random_and_private(self):
		self.login('staff', self.maria)
		self.submit(receipt=SimpleUploadedFile('Foto Resibu.PNG', PNG), amount='10')
		self.submit(receipt=SimpleUploadedFile('x.jpg', JPG), amount='11')
		names = [c.receipt.name for c in HealthClaim.objects.all()]
		for n in names:
			self.assertRegex(n, r'^health_receipts/%d/[0-9a-f]{32}\.(png|jpg)$' % self.maria.pk)
			self.assertNotIn('Foto', n)
		self.assertEqual(len(set(names)), 2)

	def test_duplicate_claim_is_rejected_but_rejected_ones_can_be_resubmitted(self):
		self.login('staff', self.maria)
		self.submit()
		self.submit()                                                              # tanggal dan jumlah sama
		self.assertEqual(HealthClaim.objects.count(), 1)
		HealthClaim.objects.update(status='rejected')
		self.submit()
		self.assertEqual(HealthClaim.objects.count(), 2)

	def test_optional_sick_leave_link_only_lists_own_approved_leaves(self):
		lt = self.lt
		mine = Leaves.objects.create(employee=self.maria, leave_type=lt, start_date=self.today(), end_date=self.today(), is_active=True, is_confirm=True)
		Leaves.objects.create(employee=self.maria, leave_type=lt, start_date=self.today(), end_date=self.today(), is_active=True, is_confirm=False)
		other = Leaves.objects.create(employee=self.boss, leave_type=lt, start_date=self.today(), end_date=self.today(), is_active=True, is_confirm=True)
		self.login('staff', self.maria)
		html = self.client.get(reverse('health-new')).content.decode()
		self.assertEqual(html.count('<option value="%d"' % mine.pk), 1)
		self.assertNotIn('<option value="%d"' % other.pk, html)
		self.submit(leave=other.pk)                                                # milik orang lain: ditolak
		self.assertEqual(HealthClaim.objects.count(), 0)
		self.submit(leave=mine.pk)
		self.assertEqual(HealthClaim.objects.get().leave, mine)

	def test_cancel_only_own_pending(self):
		c = self.claim()
		self.login('staff', self.boss)
		self.assertEqual(self.client.post(reverse('health-cancel', args=[c.pk])).status_code, 404)    # milik orang lain
		self.login('staff', self.maria)
		self.client.post(reverse('health-cancel', args=[c.pk]))
		self.assertEqual(HealthClaim.objects.count(), 0)
		d = self.claim(status='approved')
		self.client.post(reverse('health-cancel', args=[d.pk]))
		self.assertEqual(HealthClaim.objects.count(), 1)                          # sudah diputuskan: tidak bisa dibatalkan


class PrivacyAndReceiptTests(HealthBase):
	def test_only_owner_and_privileged_roles_can_download_the_receipt(self):
		c = self.claim()
		url = reverse('health-receipt', args=[c.pk])
		self.login('staff', self.maria)
		r = self.client.get(url)
		self.assertEqual(r.status_code, 200)
		self.assertIn('attachment', r['Content-Disposition'])
		self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
		self.assertIn('no-store', r['Cache-Control'])
		self.assertEqual(b''.join(r.streaming_content), PDF)
		for g in ('hr', 'president', 'admin'):
			self.login(g, self.emp('Z' + g))
			self.assertEqual(self.client.get(url).status_code, 200, g)
		for g in ('staff', 'funsionario', 'logistik', 'employee'):
			self.login(g, self.emp('Y' + g))
			self.assertEqual(self.client.get(url).status_code, 403, g)
		self.client.logout()
		self.assertEqual(self.client.get(url).status_code, 302)

	def test_missing_file_gives_404_not_500(self):
		c = self.claim()
		os.remove(c.receipt.path)
		self.login('hr', self.emp('H'))
		self.assertEqual(self.client.get(reverse('health-receipt', args=[c.pk])).status_code, 404)

	def test_lists_are_private(self):
		self.claim(self.maria, '10')
		self.claim(self.boss, '20')
		self.login('staff', self.maria)
		h = self.client.get(reverse('health-mine')).content.decode()
		self.assertIn('US$ 10', h)
		self.assertNotIn('US$ 20', h)
		self.assertEqual(self.client.get(reverse('health-all')).status_code, 403)
		for g in ('hr', 'president', 'admin'):
			self.login(g, self.emp('A' + g))
			h = self.client.get(reverse('health-all'), {'status': 'all'}).content.decode()
			self.assertIn('US$ 10', h)
			self.assertIn('US$ 20', h)

	def test_admin_does_not_expose_the_receipt_field(self):
		from django.contrib import admin
		ma = admin.site._registry[HealthClaim]
		self.assertIn('receipt', ma.exclude)


class DecisionTests(HealthBase):
	def test_president_approves_with_amount_and_marks_paid(self):
		c = self.claim(amount='100')
		self.login('president', self.boss)
		self.client.post(reverse('health-decide', args=[c.pk, 'approve']), {'approved_amount': '80.00'})
		c.refresh_from_db()
		self.assertEqual((c.status, c.approved_amount, c.decided_by.username.startswith('u_president')), ('approved', Decimal('80.00'), True))
		self.assertIsNotNone(c.decided_at)
		self.client.post(reverse('health-pay', args=[c.pk]))
		c.refresh_from_db()
		self.assertEqual(c.status, 'paid')
		self.assertIsNotNone(c.paid_at)

	def test_only_approvers_decide(self):
		c = self.claim()
		for g in ('hr', 'staff', 'logistik', 'funsionario'):
			self.login(g, self.emp('Q' + g))
			self.assertEqual(self.client.post(reverse('health-decide', args=[c.pk, 'approve']), {}).status_code, 403, g)
			self.assertEqual(self.client.post(reverse('health-pay', args=[c.pk])).status_code, 403, g)
		c.refresh_from_db()
		self.assertEqual(c.status, 'pending')

	def test_decisions_are_post_only(self):
		c = self.claim()
		self.login('admin', self.boss)
		self.assertEqual(self.client.get(reverse('health-decide', args=[c.pk, 'approve'])).status_code, 405)
		self.assertEqual(self.client.get(reverse('health-pay', args=[c.pk])).status_code, 405)

	def test_cannot_approve_own_claim_or_decide_twice_or_overpay(self):
		own = self.claim(self.boss)
		self.login('president', self.boss)
		self.client.post(reverse('health-decide', args=[own.pk, 'approve']), {})
		own.refresh_from_db()
		self.assertEqual(own.status, 'pending')
		c = self.claim(amount='50')
		self.client.post(reverse('health-decide', args=[c.pk, 'approve']), {'approved_amount': '60'})        # melebihi yang diajukan
		self.client.post(reverse('health-decide', args=[c.pk, 'approve']), {'approved_amount': '0'})
		self.client.post(reverse('health-decide', args=[c.pk, 'approve']), {'approved_amount': 'abc'})
		c.refresh_from_db()
		self.assertEqual(c.status, 'pending')
		self.client.post(reverse('health-decide', args=[c.pk, 'reject']), {'note': 'tidak lengkap'})
		self.client.post(reverse('health-decide', args=[c.pk, 'approve']), {})                              # sudah diputuskan
		c.refresh_from_db()
		self.assertEqual((c.status, c.decision_note), ('rejected', 'tidak lengkap'))
		self.client.post(reverse('health-pay', args=[c.pk]))                                                # ditolak: tak bisa dibayar
		c.refresh_from_db()
		self.assertEqual(c.status, 'rejected')

	def test_default_approved_amount_is_the_requested_amount(self):
		c = self.claim(amount='33.30')
		self.login('admin', self.boss)
		self.client.post(reverse('health-decide', args=[c.pk, 'approve']), {})
		c.refresh_from_db()
		self.assertEqual(c.approved_amount, Decimal('33.30'))

	@override_settings(MDI_HEALTH_ANNUAL_LIMIT=150)
	def test_annual_limit_is_enforced_per_employee_and_year(self):
		self.login('president', self.boss)
		a = self.claim(amount='100', claim_date=datetime.date(2026, 3, 1))
		b = self.claim(amount='100', claim_date=datetime.date(2026, 6, 1))
		c27 = self.claim(amount='140', claim_date=datetime.date(2027, 2, 1))
		other = self.claim(self.boss, amount='140', claim_date=datetime.date(2026, 2, 2))
		self.client.post(reverse('health-decide', args=[a.pk, 'approve']), {})
		self.client.post(reverse('health-decide', args=[b.pk, 'approve']), {})                               # 100 + 100 > 150
		b.refresh_from_db()
		self.assertEqual(b.status, 'pending')
		self.client.post(reverse('health-decide', args=[b.pk, 'approve']), {'approved_amount': '50'})        # pas sisa batas
		b.refresh_from_db()
		self.assertEqual(b.approved_amount, Decimal('50.00'))
		self.client.post(reverse('health-decide', args=[c27.pk, 'approve']), {})                             # tahun lain: batas baru
		c27.refresh_from_db()
		self.assertEqual(c27.status, 'approved')
		s = services.year_summary(self.maria, 2026)
		self.assertEqual((s['used'], s['limit'], s['left']), (Decimal('150.00'), Decimal('150'), Decimal('0.00')))

	def test_no_limit_by_default(self):
		self.assertIsNone(services.annual_limit())
		s = services.year_summary(self.maria, 2026)
		self.assertIsNone(s['left'])

	def test_summary_is_shown_to_the_employee(self):
		with override_settings(MDI_HEALTH_ANNUAL_LIMIT=500):
			self.login('staff', self.maria)
			h = self.client.get(reverse('health-mine')).content.decode()
		self.assertIn('Limite tinan-tinan: US$ 500', h)
		self.assertIn('Sobra: US$ 500', h)

	def test_approver_form_shows_only_for_pending_not_own(self):
		c = self.claim(self.boss)
		other = self.claim(self.maria)
		self.login('president', self.boss)
		h = self.client.get(reverse('health-all')).content.decode()
		self.assertIn(reverse('health-decide', args=[other.pk, 'approve']), h)
		self.assertNotIn(reverse('health-decide', args=[c.pk, 'approve']), h)
		self.login('hr', self.emp('HR1'))
		h = self.client.get(reverse('health-all')).content.decode()
		self.assertNotIn(reverse('health-decide', args=[other.pk, 'approve']), h)


class NotifAndI18nTests(HealthBase):
	def test_bell_counts_pending_health_for_approvers_and_broken_assets_for_managers(self):
		from assets.models import Asset, AssetCategory
		self.claim(self.maria)
		self.claim(self.boss)
		Asset.objects.create(code='B1', name='Rusak', category=AssetCategory.objects.first(), status='broken')
		self.login('president', self.boss)
		d = self.client.get(reverse('notif-badge')).json()
		self.assertEqual((d['health'], d['assets']), (1, 0))                        # klaim sendiri tidak dihitung; bukan pengelola aset
		self.login('logistik', self.emp('Log'))
		d = self.client.get(reverse('notif-badge')).json()
		self.assertEqual((d['health'], d['assets']), (0, 1))
		self.login('hr', self.emp('H2'))
		d = self.client.get(reverse('notif-badge')).json()
		self.assertEqual((d['health'], d['assets']), (0, 0))

	def test_translations_and_privacy_hint_in_four_languages(self):
		self.login('staff', self.maria)
		want = {'tet': 'Husu bónus saúde', 'en': 'Request health care bonus', 'id': 'Ajukan bonus health care', 'pt': 'Pedir bónus de saúde'}
		for lang, text in want.items():
			self.client.cookies['mdi_lang'] = lang
			self.assertContains(self.client.get(reverse('health-new')), text)
		self.client.cookies['mdi_lang'] = 'id'
		r = self.client.post(reverse('health-new'), self.data(amount='0'))
		self.assertContains(r, 'Jumlah harus lebih dari 0.')

	def test_menu_entries_per_role(self):
		self.login('staff', self.maria)
		h = self.client.get(reverse('home')).content.decode()
		self.assertIn(reverse('health-new'), h)
		self.assertNotIn(reverse('health-all'), h)
		self.login('hr', self.emp('H3'))
		self.assertIn(reverse('health-all'), self.client.get(reverse('home')).content.decode())
