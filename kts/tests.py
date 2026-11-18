import datetime
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from main import roles
from main.tests import HrBase

from . import services
from .models import Sai, SaiEvent, Tama, TamaEvent

PDF = b'%PDF-1.4\n%valid header\n'


class KtsBase(HrBase):
	"""Empat grup: admin, director, administrasaun, staff (staf juga resepsionis)."""

	def setUp(self):
		super().setUp()
		self.tmp = tempfile.mkdtemp()
		self.addCleanup(shutil.rmtree, self.tmp, True)
		ov = override_settings(MEDIA_ROOT=self.tmp)
		ov.enable()
		self.addCleanup(ov.disable)
		self.boss = self.emp('Bos', 'Besar')
		self.worker = self.emp('Joao', 'Kerja')
		self.rec = self.emp('Rita', 'Resep')
		self.u = {'admin': self.user('admin'), 'director': self.user('director', self.boss), 'administrasaun': self.user('administrasaun', self.emp('Ana', 'Adm')),
				  'staff': self.user('staff', self.rec)}
		self.uw = self.user('staff', self.worker)

	def go(self, user):
		self.client.force_login(user)

	def data(self, **kw):
		d = {'nu_ref': '001/2026', 'de': 'Ministeriu', 'para': 'MDI', 'asuntu': 'Konvite',
			'data_kartatama': timezone.localdate().isoformat(), 'entrega': 'Ana', 'obs': '',
			'file_pdf': SimpleUploadedFile('k.pdf', PDF, 'application/pdf')}
		d.update(kw)
		return d

	def register(self, **kw):
		self.go(self.u['staff'])
		r = self.client.post(reverse('kts-tama-add'), self.data(**kw))
		self.assertEqual(r.status_code, 302, getattr(r, 'content', b'')[:200])
		return Tama.objects.latest('pk')


class KtsFlowTests(KtsBase):
	def test_full_workflow(self):
		l = self.register()
		self.assertEqual(l.status, 'registered')
		self.go(self.u['administrasaun'])
		self.client.post(reverse('kts-tama-approve', args=[l.pk]))
		l.refresh_from_db()
		self.assertEqual(l.status, 'approved')
		self.go(self.u['director'])
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

	def test_only_staff_register_incoming(self):
		for g in ('admin', 'director', 'administrasaun'):
			self.go(self.u[g])
			self.assertEqual(self.client.get(reverse('kts-tama-add')).status_code, 403, g)
			self.assertEqual(self.client.post(reverse('kts-tama-add'), self.data()).status_code, 403, g)
		self.assertEqual(Tama.objects.count(), 0)
		self.go(self.u['staff'])
		self.assertEqual(self.client.get(reverse('kts-tama-add')).status_code, 200)

	def test_wrong_roles_cannot_step(self):
		l = self.register()
		for g in ('staff', 'director'):
			self.go(self.u[g])
			self.assertEqual(self.client.post(reverse('kts-tama-approve', args=[l.pk])).status_code, 403, g)
		l.refresh_from_db()
		self.assertEqual(l.status, 'registered')
		services.approve(l.pk, self.u['administrasaun'])
		for g in ('administrasaun', 'staff'):
			self.go(self.u[g])
			self.assertEqual(self.client.post(reverse('kts-tama-dispose', args=[l.pk]), {'handler': self.worker.pk, 'despacho': 'x'}).status_code, 403, g)

	def test_cannot_dispose_before_approval_and_needs_despacho(self):
		l = self.register()
		with self.assertRaises(services.LetterError):
			services.dispose(l.pk, self.u['director'], self.worker, 'x')
		services.approve(l.pk, self.u['administrasaun'])
		with self.assertRaises(services.LetterError):
			services.dispose(l.pk, self.u['director'], self.worker, '  ')
		with self.assertRaises(services.LetterError):
			services.dispose(l.pk, self.u['director'], self.worker, 'x', due_date=datetime.date(2000, 1, 1))

	def test_return_needs_note_then_edit_resubmits(self):
		l = self.register()
		with self.assertRaises(services.LetterError):
			services.send_back(l.pk, self.u['administrasaun'], '')
		services.send_back(l.pk, self.u['administrasaun'], 'PDF tidak jelas')
		l.refresh_from_db()
		self.assertEqual(l.status, 'returned')
		self.go(self.u['staff'])
		self.client.post(reverse('kts-tama-edit', args=[l.pk]), self.data(asuntu='Baru'))
		l.refresh_from_db()
		self.assertEqual((l.status, l.asuntu), ('registered', 'Baru'))

	def test_approved_letter_locked(self):
		l = self.register()
		services.approve(l.pk, self.u['administrasaun'])
		self.go(self.u['staff'])
		self.client.post(reverse('kts-tama-edit', args=[l.pk]), self.data(asuntu='Hack'))
		l.refresh_from_db()
		self.assertNotEqual(l.asuntu, 'Hack')

	def test_only_registrant_edits_the_letter(self):
		l = self.register()
		other = self.user('staff', self.emp('Lain'))
		self.go(other)
		self.assertEqual(self.client.post(reverse('kts-tama-edit', args=[l.pk]), self.data(asuntu='Hack')).status_code, 403)
		l.refresh_from_db()
		self.assertNotEqual(l.asuntu, 'Hack')

	def test_only_handler_or_director_finishes(self):
		l = self.register()
		services.approve(l.pk, self.u['administrasaun'])
		services.dispose(l.pk, self.u['director'], self.worker, 'Tratar')
		self.go(self.user('staff', self.emp('Outru')))
		self.assertEqual(self.client.post(reverse('kts-tama-done', args=[l.pk]), {'note': 'x'}).status_code, 403)
		l.refresh_from_db()
		self.assertEqual(l.status, 'disposed')

	def test_pdf_validation(self):
		self.go(self.u['staff'])
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
		for g in ('admin', 'director', 'administrasaun', 'staff'):        # staff = pendaftar
			self.go(self.u[g])
			r = self.client.get(url)
			self.assertEqual((r.status_code, r['Content-Type']), (200, 'application/pdf'), g)
		self.go(self.uw)                                                    # staf lain, bukan pendaftar/penanggung jawab
		self.assertEqual(self.client.get(url).status_code, 403)
		services.approve(l.pk, self.u['administrasaun'])
		services.dispose(l.pk, self.u['director'], self.worker, 'x')
		self.assertEqual(self.client.get(url).status_code, 200)             # penanggung jawab boleh
		self.client.logout()
		self.assertEqual(self.client.get(url).status_code, 302)

	def test_staff_see_only_letters_they_registered_or_handle(self):
		a = self.register()
		self.go(self.uw)
		self.assertEqual(self.client.get(reverse('kts-tama')).status_code, 200)
		self.assertNotContains(self.client.get(reverse('kts-tama')), '001/2026')
		self.assertEqual(self.client.get(reverse('kts-tama-detail', args=[a.pk])).status_code, 403)
		self.go(self.u['staff'])
		self.assertContains(self.client.get(reverse('kts-tama')), '001/2026')
		services.approve(a.pk, self.u['administrasaun'])
		services.dispose(a.pk, self.u['director'], self.worker, 'x')
		self.go(self.uw)
		self.assertContains(self.client.get(reverse('kts-tama-mine')), '001/2026')
		self.assertEqual(self.client.get(reverse('kts-tama-detail', args=[a.pk])).status_code, 200)

	def test_actions_are_post_only(self):
		l = self.register()
		self.go(self.u['administrasaun'])
		self.assertEqual(self.client.get(reverse('kts-tama-approve', args=[l.pk])).status_code, 405)


class KtsOutgoingTests(KtsBase):
	"""Surat keluar: dibuat siapa saja, diverifikasi administrasi, disetujui direktur."""

	def sai(self, **kw):
		d = {'nu_ref': 'S-1', 'de': 'MDI', 'para': 'Ministeriu', 'asuntu': 'Resposta', 'data_kartasai': timezone.localdate().isoformat(), 'obs': '',
			'file_pdf': SimpleUploadedFile('s.pdf', PDF, 'application/pdf')}
		d.update(kw)
		return d

	def create(self, group='staff', **kw):
		self.go(self.u[group])
		r = self.client.post(reverse('kts-sai-add'), self.sai(**kw))
		self.assertEqual(r.status_code, 302, getattr(r, 'content', b'')[:200])
		return Sai.objects.latest('pk')

	def test_everyone_can_create_outgoing(self):
		for i, g in enumerate(('admin', 'director', 'administrasaun', 'staff')):
			s = self.create(g, nu_ref='S-%d' % i)
			self.assertEqual((s.status, s.user_id), ('registered', self.u[g].pk))
		self.assertEqual(Sai.objects.count(), 4)

	def test_full_outgoing_workflow(self):
		s = self.create()
		self.go(self.u['administrasaun'])
		self.assertEqual(self.client.post(reverse('kts-sai-verify', args=[s.pk]), {'note': 'ok'}).status_code, 302)
		s.refresh_from_db()
		self.assertEqual((s.status, s.verified_by_id), ('verified', self.u['administrasaun'].pk))
		self.go(self.u['director'])
		self.client.post(reverse('kts-sai-approve', args=[s.pk]), {'note': 'setuju'})
		s.refresh_from_db()
		self.assertEqual((s.status, s.approved_by_id), ('approved', self.u['director'].pk))
		self.assertEqual(list(SaiEvent.objects.filter(letter=s).order_by('pk').values_list('action', flat=True)), ['register', 'verify', 'approve'])

	def test_roles_for_each_step(self):
		s = self.create()
		for g in ('staff', 'director'):                                     # direktur tidak melompati verifikasi
			self.go(self.u[g])
			self.client.post(reverse('kts-sai-verify', args=[s.pk]))
			s.refresh_from_db()
			self.assertEqual(s.status, 'registered', g)
		for g in ('staff', 'administrasaun'):
			self.go(self.u[g])
			self.client.post(reverse('kts-sai-approve', args=[s.pk]))
			s.refresh_from_db()
			self.assertEqual(s.status, 'registered', g)
		self.go(self.u['staff'])
		self.assertEqual(self.client.post(reverse('kts-sai-verify', args=[s.pk])).status_code, 403)
		self.assertEqual(self.client.post(reverse('kts-sai-approve', args=[s.pk])).status_code, 403)

	def test_cannot_approve_before_verified_or_verify_own_letter(self):
		s = self.create('administrasaun')
		with self.assertRaises(services.LetterError):
			services.sai_approve(s.pk, self.u['director'])
		with self.assertRaises(services.LetterError) as cm:
			services.sai_verify(s.pk, self.u['administrasaun'])                # surat buatan sendiri
		self.assertEqual(cm.exception.key, 'kts.err.self_verify')
		services.sai_verify(s.pk, self.u['admin'])                              # admin sistem boleh sebagai pengganti

	def test_return_needs_note_and_resubmit_goes_through_again(self):
		s = self.create()
		services.sai_verify(s.pk, self.u['administrasaun'])
		with self.assertRaises(services.LetterError):
			services.sai_return(s.pk, self.u['director'], ' ')
		services.sai_return(s.pk, self.u['director'], 'Ubah isi')
		s.refresh_from_db()
		self.assertEqual((s.status, s.approve_note), ('returned', 'Ubah isi'))
		self.go(self.u['staff'])
		self.client.post(reverse('kts-sai-edit', args=[s.pk]), self.sai(asuntu='Revisi'))
		s.refresh_from_db()
		self.assertEqual((s.status, s.asuntu), ('registered', 'Revisi'))

	def test_return_step_depends_on_stage(self):
		s = self.create()
		self.go(self.u['director'])                                         # direktur belum boleh mengembalikan yang belum diverifikasi
		self.client.post(reverse('kts-sai-return', args=[s.pk]), {'note': 'x'})
		s.refresh_from_db()
		self.assertEqual(s.status, 'registered')
		self.go(self.u['administrasaun'])
		self.client.post(reverse('kts-sai-return', args=[s.pk]), {'note': 'perbaiki'})
		s.refresh_from_db()
		self.assertEqual(s.status, 'returned')

	def test_approved_letter_is_locked(self):
		s = self.create()
		services.sai_verify(s.pk, self.u['administrasaun'])
		services.sai_approve(s.pk, self.u['director'])
		self.go(self.u['staff'])
		self.client.post(reverse('kts-sai-edit', args=[s.pk]), self.sai(asuntu='Hack'))
		s.refresh_from_db()
		self.assertNotEqual(s.asuntu, 'Hack')

	def test_visibility_staff_own_only_others_all(self):
		mine = self.create('staff', nu_ref='S-MINE')
		self.go(self.uw)
		self.assertNotContains(self.client.get(reverse('kts-sai')), 'S-MINE')
		self.assertEqual(self.client.get(reverse('kts-sai-detail', args=[mine.pk])).status_code, 403)
		self.assertEqual(self.client.get(reverse('kts-sai-file', args=[mine.pk])).status_code, 403)
		self.assertEqual(self.client.post(reverse('kts-sai-edit', args=[mine.pk]), self.sai(asuntu='Hack')).status_code, 403)
		for g in ('staff', 'admin', 'director', 'administrasaun'):
			self.go(self.u[g])
			self.assertContains(self.client.get(reverse('kts-sai')), 'S-MINE')
			self.assertEqual(self.client.get(reverse('kts-sai-file', args=[mine.pk])).status_code, 200, g)

	def test_unique_reference_per_year(self):
		self.create()
		self.client.post(reverse('kts-sai-add'), self.sai())
		self.assertEqual(Sai.objects.count(), 1)

	def test_queues_in_dash_and_counts(self):
		s = self.create()
		c = services.counts_for(self.u['administrasaun'], None, roles)
		self.assertEqual((c['out_verify'], c['out_approve']), (1, 0))
		services.sai_verify(s.pk, self.u['administrasaun'])
		c = services.counts_for(self.u['director'], None, roles)
		self.assertEqual((c['out_verify'], c['out_approve']), (0, 1))
		services.sai_return(s.pk, self.u['director'], 'perbaiki')
		self.assertEqual(services.counts_for(self.u['staff'], None, roles)['out_returned'], 1)
		self.go(self.u['staff'])
		self.assertContains(self.client.get(reverse('kts-dash')), 'KARTA SAI')


class KtsMiscTests(KtsBase):
	def test_dash_and_counts_per_role(self):
		self.register()
		self.go(self.u['administrasaun'])
		self.assertContains(self.client.get(reverse('kts-dash')), 'KARTA TAMA')
		c = services.counts_for(self.u['administrasaun'], None, roles)
		self.assertEqual(c['verify'], 1)

	def test_bell_counts_tasks(self):
		self.register()
		self.go(self.u['administrasaun'])
		self.assertEqual(self.client.get(reverse('notif-badge')).json()['kts'], 1)

	def test_admin_is_read_only(self):
		from django.contrib import admin
		for m in (Tama, Sai, TamaEvent, SaiEvent):
			ma = admin.site._registry[m]
			self.assertFalse(ma.has_add_permission(None))
			self.assertFalse(ma.has_delete_permission(None))

	def test_other_languages_render(self):
		l = self.register()
		s = Sai.objects.create(nu_ref='S-9', de='MDI', para='X', asuntu='Y', data_kartasai=timezone.localdate(), user=self.u['staff'], status='verified')
		self.go(self.u['director'])
		for lang in ('en', 'id', 'pt'):
			self.client.cookies['mdi_lang'] = lang
			for url in (reverse('kts-tama-detail', args=[l.pk]), reverse('kts-sai-detail', args=[s.pk]), reverse('kts-sai'), reverse('kts-dash')):
				r = self.client.get(url)
				self.assertEqual(r.status_code, 200, url)
				self.assertNotContains(r, 'Hein verifikasaun')
				self.assertNotContains(r, 'hein aprovasaun')
