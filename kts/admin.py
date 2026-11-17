from django.contrib import admin

from .models import Sai, Tama, TamaEvent


class ReadOnly(admin.ModelAdmin):
	"""Alur surat milik pengguna di aplikasi (resepsionis, administrasi, direktur): admin Django hanya melihat."""
	exclude = ('file_pdf', 'done_file')

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False

	def has_delete_permission(self, request, obj=None):
		return False


@admin.register(Tama)
class TamaAdmin(ReadOnly):
	list_display = ('nu_ref', 'de', 'asuntu', 'data_kartatama', 'status', 'handler')
	list_filter = ('status', 'anu_letivu')
	search_fields = ('nu_ref', 'de', 'asuntu')


@admin.register(Sai)
class SaiAdmin(ReadOnly):
	list_display = ('nu_ref', 'para', 'asuntu', 'data_kartasai')
	search_fields = ('nu_ref', 'para', 'asuntu')


@admin.register(TamaEvent)
class TamaEventAdmin(ReadOnly):
	list_display = ('at', 'letter', 'action', 'user')
