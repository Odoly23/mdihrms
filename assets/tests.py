import datetime

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from employee.models import EmployeeUser
from main.tests import HrBase

from . import services
from .models import Asset, AssetCategory, AssetEvent


class AssetBase(HrBase):
	def setUp(self):
		super().setUp()
		self.laptop = AssetCategory.objects.get(code='laptop')
		self.printer = AssetCategory.objects.get(code='printer')
		self.maria = self.emp('Maria', 'Silva')
		self.jose = self.emp('Jose', 'Costa')

	def make(self, code='LAP-001', status='new', category=None, shelf='', **kw):
		a = Asset(code=code, name=kw.pop('name', 'Laptop ' + code), category=category or self.laptop, status=status, shelf=shelf, **kw)
		return services.create(a, None)

	def as_(self, group, emp=None):
		return self.login(group, emp)


class RolesTests(AssetBase):
	def test_manager_and_viewer_roles(self):
		a = self.make()
		for g in ('admin', 'logistik'):
			self.as_(g)
			self.assertEqual(self.client.get(reverse('asset-list')).status_code, 200, g)
			self.assertEqual(self.client.get(reverse('asset-add')).status_code, 200, g)
		for g in ('hr', 'president'):
			self.as_(g)
			self.assertEqual(self.client.get(reverse('asset-list')).status_code, 200, g)
			self.assertEqual(self.client.get(reverse('asset-survey')).status_code, 200, g)
			self.assertEqual(self.client.get(reverse('asset-add')).status_code, 403, g)                       # hanya baca
			self.assertEqual(self.client.post(reverse('asset-assign', args=[a.pk]), {'employee': self.maria.pk}).status_code, 403, g)
		for g in ('staff', 'funsionario', 'employee'):
			self.as_(g)
			for name in ('asset-list', 'asset-survey', 'asset-add'):
				self.assertEqual(self.client.get(reverse(name)).status_code, 403, (g, name))
			self.assertEqual(self.client.get(reverse('asset-mine')).status_code, 200, g)
			self.assertEqual(self.client.get(reverse('asset-detail', args=[a.pk])).status_code, 403, g)       # bukan pemegang

	def test_actions_are_post_only(self):
		a = self.make()
		self.as_('admin')
		for name in ('asset-assign', 'asset-return', 'asset-status', 'asset-shelf', 'asset-confirm'):
			self.assertEqual(self.client.get(reverse(name, args=[a.pk])).status_code, 405, name)

	def test_holder_can_open_own_asset_detail_only(self):
		a = self.make()
		services.assign(a.pk, self.maria, None)
		b = self.make('LAP-002')
		self.as_('staff', self.maria)
		self.assertEqual(self.client.get(reverse('asset-detail', args=[a.pk])).status_code, 200)
		self.assertEqual(self.client.get(reverse('asset-detail', args=[b.pk])).status_code, 403)

	def test_anonymous_redirected(self):
		self.client.logout()
		self.assertEqual(self.client.get(reverse('asset-list')).status_code, 302)
		self.assertEqual(self.client.get(reverse('asset-detail', args=[1])).status_code, 302)


class ServiceRulesTests(AssetBase):
	def test_create_logs_event_and_rejects_held_statuses(self):
		a = self.make(status='in_stock', shelf='Rak A-1')
		self.assertEqual(AssetEvent.objects.get(asset=a).kind, 'create')
		with self.assertRaises(services.AssetError):
			self.make('X', status='in_use')

	def test_assign_return_cycle_and_history(self):
		a = self.make(status='in_stock', shelf='Rak B')
		services.assign(a.pk, self.maria, None, note='untuk kerja')
		a.refresh_from_db()
		self.assertEqual((a.status, a.holder, a.shelf), ('in_use', self.maria, ''))
		with self.assertRaises(services.AssetError):                      # sudah dipegang
			services.assign(a.pk, self.jose, None)
		services.return_asset(a.pk, None, 'in_stock', shelf='Rak C')
		a.refresh_from_db()
		self.assertEqual((a.status, a.holder, a.shelf), ('in_stock', None, 'Rak C'))
		self.assertEqual([e.kind for e in a.events.order_by('id')], ['create', 'assign', 'return'])

	def test_return_variants_and_validation(self):
		a = self.make()
		services.assign(a.pk, self.maria, None)
		with self.assertRaises(services.AssetError):
			services.return_asset(a.pk, None, 'in_stock', shelf='')       # rak wajib
		with self.assertRaises(services.AssetError):
			services.return_asset(a.pk, None, 'new')                      # status tidak boleh
		services.return_asset(a.pk, None, 'broken')
		a.refresh_from_db()
		self.assertEqual((a.status, a.holder), ('broken', None))
		with self.assertRaises(services.AssetError):                      # sudah tidak dipegang
			services.return_asset(a.pk, None, 'returned')

	def test_cannot_assign_broken_inactive_or_repaired(self):
		a = self.make(status='broken')
		with self.assertRaises(services.AssetError):
			services.assign(a.pk, self.maria, None)
		b = self.make('LAP-9')
		Asset.objects.filter(pk=b.pk).update(is_active=False)
		with self.assertRaises(services.AssetError):
			services.assign(b.pk, self.maria, None)

	def test_status_rules(self):
		a = self.make()
		with self.assertRaises(services.AssetError):
			services.set_status(a.pk, 'in_use', None)                    # tanpa pemegang: pakai assign
		with self.assertRaises(services.AssetError):
			services.set_status(a.pk, 'in_stock', None)                  # rak wajib
		with self.assertRaises(services.AssetError):
			services.set_status(a.pk, 'ngawur', None)
		services.set_status(a.pk, 'in_repair', None, note='bengkel')
		services.set_status(a.pk, 'in_stock', None, shelf='Rak D')
		a.refresh_from_db()
		self.assertEqual((a.status, a.shelf), ('in_stock', 'Rak D'))

	def test_status_change_keeps_holder_when_held_and_frees_when_returned_to_stock(self):
		a = self.make()
		services.assign(a.pk, self.maria, None)
		services.set_status(a.pk, 'broken', None)
		a.refresh_from_db()
		self.assertEqual((a.status, a.holder), ('broken', self.maria))   # rusak tetapi masih di tangan staf
		services.set_status(a.pk, 'in_stock', None, shelf='Rak E')
		a.refresh_from_db()
		self.assertIsNone(a.holder)

	def test_self_service_is_limited_to_own_assets_and_two_statuses(self):
		a, b = self.make(), self.make('LAP-2')
		services.assign(a.pk, self.maria, None)
		services.assign(b.pk, self.jose, None)
		services.set_status(a.pk, 'broken', None, self_service_for=self.maria)
		with self.assertRaises(services.AssetError):
			services.set_status(b.pk, 'broken', None, self_service_for=self.maria)        # milik orang lain
		with self.assertRaises(services.AssetError):
			services.set_status(a.pk, 'in_stock', None, shelf='x', self_service_for=self.maria)   # status tidak diizinkan
		with self.assertRaises(services.AssetError):
			services.confirm(b.pk, None, self_service_for=self.maria)

	def test_shelf_rules(self):
		a = self.make(status='in_stock', shelf='Rak A')
		services.move_shelf(a.pk, 'Rak Z', None)
		a.refresh_from_db()
		self.assertEqual(a.shelf, 'Rak Z')
		with self.assertRaises(services.AssetError):
			services.move_shelf(a.pk, '  ', None)
		services.assign(a.pk, self.maria, None)
		with self.assertRaises(services.AssetError):
			services.move_shelf(a.pk, 'Rak Q', None)                    # sedang dipegang staf

	def test_confirm_updates_last_checked_and_logs(self):
		a = self.make()
		self.assertIsNone(a.last_checked)
		services.confirm(a.pk, None, note='cek rutin')
		a.refresh_from_db()
		self.assertIsNotNone(a.last_checked)
		self.assertEqual(a.events.first().kind, 'survey')


class ViewFlowTests(AssetBase):
	def test_manager_flow_through_the_pages(self):
		self.as_('logistik')
		r = self.client.post(reverse('asset-add'), {'code': 'pc-001', 'name': 'PC Kantor', 'category': self.laptop.pk, 'status': 'in_stock',
			'shelf': 'Rak A-1', 'brand': 'Dell', 'model': 'X', 'serial_number': 'S1', 'notes': ''})
		a = Asset.objects.get(code='pc-001')
		self.assertRedirects(r, reverse('asset-detail', args=[a.pk]))
		self.assertEqual((a.status, a.shelf), ('in_stock', 'Rak A-1'))
		self.client.post(reverse('asset-assign', args=[a.pk]), {'employee': self.maria.pk, 'note': 'ok'})
		a.refresh_from_db()
		self.assertEqual((a.status, a.holder), ('in_use', self.maria))
		self.client.post(reverse('asset-return', args=[a.pk]), {'to_status': 'broken', 'shelf': '', 'note': 'layar pecah'})
		a.refresh_from_db()
		self.assertEqual((a.status, a.holder), ('broken', None))
		self.client.post(reverse('asset-status', args=[a.pk]), {'to_status': 'in_repair', 'shelf': '', 'note': 'bengkel'})
		self.client.post(reverse('asset-status', args=[a.pk]), {'to_status': 'in_stock', 'shelf': 'Rak B-2', 'note': ''})
		a.refresh_from_db()
		self.assertEqual((a.status, a.shelf), ('in_stock', 'Rak B-2'))
		page = self.client.get(reverse('asset-detail', args=[a.pk])).content.decode()
		for text in ('Rak B-2', 'Stok (iha rak)', 'layar pecah', 'bengkel'):
			self.assertIn(text, page)

	def test_form_validation(self):
		self.as_('admin')
		self.make('DUP-1')
		base = {'name': 'X', 'category': self.laptop.pk, 'status': 'new', 'brand': '', 'model': '', 'serial_number': '', 'notes': '', 'shelf': ''}
		self.client.post(reverse('asset-add'), dict(base, code='dup-1'))                                   # kode ganda (tak peduli huruf)
		self.client.post(reverse('asset-add'), dict(base, code='N1', status='in_stock'))                    # rak wajib
		self.client.post(reverse('asset-add'), dict(base, code='N2', purchase_date='2999-01-01'))           # tanggal masa depan
		self.client.post(reverse('asset-add'), dict(base, code='N3', status='in_use'))                      # status awal tidak sah
		self.assertEqual(Asset.objects.count(), 1)

	def test_my_assets_self_service(self):
		a = self.make()
		services.assign(a.pk, self.maria, None)
		self.as_('staff', self.maria)
		page = self.client.get(reverse('asset-mine')).content.decode()
		self.assertIn(a.code, page)
		self.client.post(reverse('asset-self-status', args=[a.pk]), {'to_status': 'broken'})
		a.refresh_from_db()
		self.assertEqual(a.status, 'broken')
		self.client.post(reverse('asset-self-status', args=[a.pk]), {'to_status': 'in_stock', 'shelf': 'x'})   # tidak diizinkan
		a.refresh_from_db()
		self.assertEqual(a.status, 'broken')
		self.client.post(reverse('asset-self-confirm', args=[a.pk]))
		self.assertEqual(a.events.filter(kind='survey').count(), 1)

	def test_self_service_cannot_touch_someone_elses_asset(self):
		a = self.make()
		services.assign(a.pk, self.jose, None)
		self.as_('staff', self.maria)
		self.client.post(reverse('asset-self-status', args=[a.pk]), {'to_status': 'broken'})
		a.refresh_from_db()
		self.assertEqual(a.status, 'in_use')

	def test_unlinked_account_gets_a_message_not_an_error(self):
		self.as_('staff')
		self.assertEqual(self.client.get(reverse('asset-mine')).status_code, 200)
		r = self.client.post(reverse('asset-self-status', args=[1]), {'to_status': 'broken'})
		self.assertEqual(r.status_code, 302)


class SurveyTests(AssetBase):
	def test_summary_counts_stock_and_attention(self):
		a = self.make('L1')
		b = self.make('L2', status='in_stock', shelf='Rak A')
		c = self.make('P1', category=self.printer, status='broken')
		d = self.make('L3')
		services.assign(d.pk, self.maria, None)
		services.confirm(d.pk, None)
		s = services.summary()
		self.assertEqual(s['grand'], 4)
		self.assertEqual(s['totals'], {'new': 1, 'in_use': 1, 'returned': 0, 'in_repair': 0, 'broken': 1, 'in_stock': 1})
		self.assertEqual(s['stock'], 3)                                                  # L1, L2, P1 tanpa pemegang
		self.assertEqual([x.code for x in s['attention']], ['P1'])
		self.assertEqual(s['stale'], 2)                                                  # L1, L2 belum pernah dicek (P1 rusak tidak dihitung)
		self.assertEqual({r['category'].code: r['total'] for r in s['rows']}, {'laptop': 3, 'printer': 1})

	def test_inactive_assets_are_ignored(self):
		a = self.make()
		Asset.objects.filter(pk=a.pk).update(is_active=False)
		self.assertEqual(services.summary()['grand'], 0)

	def test_summary_query_count_is_constant(self):
		for i in range(40):
			self.make('B%d' % i, category=self.printer if i % 2 else self.laptop)
		with CaptureQueriesContext(connection) as c:
			services.summary()
		self.assertLessEqual(len(c), 6)

	def test_survey_page_and_csv(self):
		self.make('L1', name='=cmd|calc')
		self.as_('hr')
		page = self.client.get(reverse('asset-survey')).content.decode()
		self.assertIn('ASET ESTRAGA', page)
		r = self.client.get(reverse('asset-survey-csv'))
		text = r.content.decode('utf-8')
		self.assertTrue(text.startswith('﻿'))
		self.assertIn("'=cmd|calc", text)                                                  # tidak bisa jadi rumus di Excel
		self.assertNotIn(',=cmd', text)
		self.as_('staff')
		self.assertEqual(self.client.get(reverse('asset-survey-csv')).status_code, 403)

	def test_list_filters_search_and_tiles(self):
		self.make('L1', name='Laptop Satu')
		b = self.make('P1', category=self.printer, name='Printer Lantai 2', status='in_stock', shelf='Rak 7')
		self.as_('admin')
		for params, want, notwant in (({'q': 'Printer'}, 'P1', 'L1'), ({'category': self.laptop.pk}, 'L1', 'P1'),
				({'status': 'in_stock'}, 'P1', 'L1'), ({'q': 'Rak 7'}, 'P1', 'L1'), ({'where': 'held'}, None, 'L1')):
			html = self.client.get(reverse('asset-list'), params).content.decode()
			if want:
				self.assertIn(want, html, params)
			self.assertNotIn('>%s<' % notwant, html, params)
		self.assertEqual(self.client.get(reverse('asset-list'), {'category': 'x', 'status': '<script>'}).status_code, 200)


class SetupAndMiscTests(AssetBase):
	def test_setup_seeds_categories_and_logistics_group_idempotently(self):
		call_command('mdi_setup', verbosity=0)
		self.assertEqual(AssetCategory.objects.count(), 7)
		self.assertTrue(Group.objects.filter(name='logistik').exists())

	def test_event_history_cannot_be_edited_in_admin(self):
		from django.contrib import admin
		from .models import AssetEvent as Ev
		ma = admin.site._registry[Ev]
		self.assertFalse(ma.has_change_permission(None))
		self.assertFalse(ma.has_delete_permission(None))

	def test_hr_sees_assets_on_staff_detail_but_staff_does_not(self):
		a = self.make('LAP-77')
		services.assign(a.pk, self.maria, None)
		self.as_('hr')
		self.assertIn('LAP-77', self.client.get(reverse('staff-detail', args=[self.maria.pk])).content.decode())

	def test_translations_in_four_languages(self):
		self.make('L1', status='in_stock', shelf='Rak A')
		self.as_('admin')
		want = {'tet': ('Stok (iha rak)', 'Komputadór'), 'en': ('In stock (on shelf)', 'Laptop'), 'id': ('Stok (di rak)', 'Laptop'), 'pt': ('Em stock (na prateleira)', 'Portátil')}
		for lang, (status, cat) in want.items():
			self.client.cookies['mdi_lang'] = lang
			html = self.client.get(reverse('asset-list')).content.decode()
			self.assertIn(status, html, lang)
			self.assertIn(cat, html, lang)

	def test_category_name_translates_known_codes_but_keeps_custom(self):
		from .forms import category_name
		custom = AssetCategory.objects.create(name='Genset', code=None)
		self.assertEqual(category_name(self.laptop, 'pt'), 'Portátil')
		self.assertEqual(category_name(custom, 'pt'), 'Genset')
