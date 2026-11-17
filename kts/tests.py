import datetime
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from main.tests import HrBase

from . import services
from .models import Sai, Tama, TamaEvent

PDF = b'%PDF-1.4\n%valid header\n'


class KtsBase(HrBase):
	def setUp(self):
		super().setUp()
		self.tmp = tempfile.mkdtemp()
		self.addCleanup(shutil.rmtree, self.tmp, True)
		ov = override_settings(MEDIA_ROOT=self.tmp)
		ov.enable()
		self.addCleanup(ov.disable)
		self.boss = self.emp('Bos', 'Besar')
		self.worker = self.emp('Joao', 'Kerja')
		self.u = {g: self.user(g, e) for g, e in (('resepsionis', None), ('admin', None), ('president', self.boss), ('staff', None))}
		self.uw = self.user('employee', self.worker)

	def go(self, user):
		self.client.force_login(user)

	def data(self, **kw):
		d = {'nu_ref': '001/2026', 'de': 'Ministeriu', 'para': 'MDI', 'asuntu': 'Konvite',
			'data_kartatama': timezone.localdate().isoformat(), 'entrega': 'Ana', 'obs': '',
			'file_pdf': SimpleUploadedFile('k.pdf', PDF, 'application/pdf')}
		d.update(kw)
		return d

	def register(self, **kw):
		self.go(self.u['resepsionis'])
		r = self.client.post(reverse('kts-tama-add'), self.data(**kw))
		self.assertEqual(r.status_code, 302, getattr(r, 'content', b'')[:200])
		return Tama.objects.latest('pk')


class KtsFlowTests(KtsBase):
	def test_full_workflow(self):
		l = self.register()
		self.assertEqual(l.status, 'registered')
		self.go(self.u['admin'])
		self.client.post(reverse('kts-tama-approve', args=[l.pk]))
		l.refresh_from_db()
		self.assertEqual(l.status, 'approved')
		self.go(self.u['president'])
		r = self.client.post(reverse('kts-tama-dispose', args=[l.pk]), {'handler': self.worker.pk, 'despacho': 'Tratar', 'due_date': ''})
		self.assertEqual(r.status_code, 302)
		l.refresh_from_db()
		self.assertEqual((l.status, l.handler_id), ('disposed', self.worker.pk))
		self.go(self.uw)
		self.assertContains(self.client.get(reverse('kts-tama-mine')), '001/2026')
		self.client.post(reverse('kts-tama-done', args=[l.pk]), {'note': 'Hotu ona'})
		l.refresh_from_db()
		self.assertEqual(l.status, 'done')
		self.assertEqual(list(TamaEvent.objects.filter(letter=l).order_by('pk').values_list('action', flat=True)),
			['register', 'approve', 'dispose', 'done'])

	def test_only_receptionist_registers(self):
		for g in ('admin', 'president', 'staff'):
			self.go(self.u[g])
			self.assertEqual(self.client.get(reverse('kts-tama-add')).status_code, 403, g)
			self.assertEqual(self.client.post(reverse('kts-tama-add'), self.data()).status_code, 403, g)
		self.assertEqual(Tama.objects.count(), 0)

	def test_wrong_roles_cannot_step(self):
		l = self.register()
		for g in ('resepsionis', 'president', 'staff'):
			self.go(self.u[g])
			self.assertEqual(self.client.post(reverse('kts-tama-approve', args=[l.pk])).status_code, 403, g)
		l.refresh_from_db()
		self.assertEqual(l.status, 'registered')
		services.approve(l.pk, self.u['admin'])
		self.go(self.u['admin'])
		self.assertEqual(self.client.post(reverse('kts-tama-dispose', args=[l.pk]), {'handler': self.worker.pk, 'despacho': 'x'}).status_code, 403)

	def test_cannot_dispose_before_approval_and_needs_despacho(self):
		l = self.register()
		with self.assertRaises(services.LetterError):
			services.dispose(l.pk, self.u['president'], self.worker, 'x')
		services.approve(l.pk, self.u['admin'])
		with self.assertRaises(services.LetterError):
			services.dispose(l.pk, self.u['president'], self.worker, '  ')
		with self.assertRaises(services.LetterError):
			services.dispose(l.pk, self.u['president'], self.worker, 'x', due_date=datetime.date(2000, 1, 1))

	def test_return_needs_note_then_edit_resubmits(self):
		l = self.register()
		with self.assertRaises(services.LetterError):
			services.send_back(l.pk, self.u['admin'], '')
		services.send_back(l.pk, self.u['admin'], 'PDF tidak jelas')
		l.refresh_from_db()
		self.assertEqual(l.status, 'returned')
		self.go(self.u['resepsionis'])
		self.client.post(reverse('kts-tama-edit', args=[l.pk]), self.data(asuntu='Baru'))
		l.refresh_from_db()
		self.assertEqual((l.status, l.asuntu), ('registered', 'Baru'))

	def test_approved_letter_locked(self):
		l = self.register()
		services.approve(l.pk, self.u['admin'])
		self.go(self.u['resepsionis'])
		self.client.post(reverse('kts-tama-edit', args=[l.pk]), self.data(asuntu='Hack'))
		l.refresh_from_db()
		self.assertNotEqual(l.asuntu, 'Hack')

	def test_only_handler_or_president_finishes(self):
		l = self.register()
		services.approve(l.pk, self.u['admin'])
		services.dispose(l.pk, self.u['president'], self.worker, 'Tratar')
		other = self.user('employee', self.emp('Outru'))
		self.go(other)
		self.assertEqual(self.client.post(reverse('kts-tama-done', args=[l.pk]), {'note': 'x'}).status_code, 403)
		l.refresh_from_db()
		self.assertEqual(l.status, 'disposed')

	def test_pdf_validation(self):
		self.go(self.u['resepsionis'])
		bad = SimpleUploadedFile('k.pdf', b'GIF89a not a pdf', 'application/pdf')
		self.client.post(reverse('kts-tama-add'), self.data(file_pdf=bad))
		self.assertEqual(Tama.objects.count(), 0)

	def test_duplicate_incoming_rejected(self):
		self.register()
		self.client.post(reverse('kts-tama-add'), self.data())
		self.assertEqual(Tama.objects.count(), 1)

	def test_file_access_control(self):
		l = self.register()
		url = reverse('kts-tama-file', args=[l.pk])
		self.go(self.u['admin'])
		r = self.client.get(url)
		self.assertEqual((r.status_code, r['Content-Type']), (200, 'application/pdf'))
		self.go(self.u['staff'])
		self.assertEqual(self.client.get(url).status_code, 403)
		self.go(self.uw)
		self.assertEqual(self.client.get(url).status_code, 403)
		services.approve(l.pk, self.u['admin'])
		services.dispose(l.pk, self.u['president'], self.worker, 'x')
		self.assertEqual(self.client.get(url).status_code, 200)   # penanggung jawab boleh
		self.client.logout()
		self.assertEqual(self.client.get(url).status_code, 302)

	def test_handler_sees_only_own_letters(self):
		a = self.register()
		self.register(nu_ref='002/2026', file_pdf=SimpleUploadedFile('k.pdf', PDF, 'application/pdf'))
		services.approve(a.pk, self.u['admin'])
		services.dispose(a.pk, self.u['president'], self.worker, 'x')
		self.go(self.uw)
		self.assertEqual(self.client.get(reverse('kts-tama')).status_code, 403)
		r = self.client.get(reverse('kts-tama-mine'))
		self.assertContains(r, '001/2026')
		self.assertNotContains(r, '002/2026')

	def test_actions_are_post_only(self):
		l = self.register()
		self.go(self.u['admin'])
		self.assertEqual(self.client.get(reverse('kts-tama-approve', args=[l.pk])).status_code, 405)


class KtsOutAndMiscTests(KtsBase):
	def sai(self, **kw):
		d = {'nu_ref': 'S-1', 'de': 'MDI', 'para': 'Ministeriu', 'asuntu': 'Resposta', 'data_kartasai': timezone.localdate().isoformat(), 'obs': ''}
		d.update(kw)
		return d

	def test_outgoing_roles_and_unique(self):
		self.go(self.u['resepsionis'])
		self.assertEqual(self.client.post(reverse('kts-sai-add'), self.sai()).status_code, 302)
		self.client.post(reverse('kts-sai-add'), self.sai())
		self.assertEqual(Sai.objects.count(), 1)
		for g in ('president', 'staff'):
			self.go(self.u[g])
			self.assertEqual(self.client.post(reverse('kts-sai-add'), self.sai(nu_ref='S-2')).status_code, 403, g)

	def test_dash_and_counts_per_role(self):
		l = self.register()
		self.go(self.u['admin'])
		self.assertContains(self.client.get(reverse('kts-dash')), 'KARTA TAMA')
		c = services.counts_for(self.u['admin'], None, __import__('main.roles', fromlist=['x']))
		self.assertEqual(c['verify'], 1)
		self.go(self.u['staff'])
		self.assertEqual(self.client.get(reverse('kts-dash')).status_code, 403)

	def test_bell_counts_tasks(self):
		self.register()
		self.go(self.u['admin'])
		self.assertEqual(self.client.get(reverse('notif-badge')).json()['kts'], 1)

	def test_admin_is_read_only(self):
		from django.contrib import admin
		for m in (Tama, Sai, TamaEvent):
			ma = admin.site._registry[m]
			self.assertFalse(ma.has_add_permission(None))
			self.assertFalse(ma.has_delete_permission(None))

	def test_other_languages_render(self):
		l = self.register()
		self.go(self.u['admin'])
		for lang in ('en', 'id', 'pt'):
			self.client.cookies['mdi_lang'] = lang
			r = self.client.get(reverse('kts-tama-detail', args=[l.pk]))
			self.assertEqual(r.status_code, 200)
			self.assertNotContains(r, 'Hein verifikasaun')
