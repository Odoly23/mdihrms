from django.contrib import admin

from .models import HealthClaim


@admin.register(HealthClaim)
class ClaimAdmin(admin.ModelAdmin):
	"""Hanya lihat: keputusan klaim milik direktur lewat halaman Health care, tidak bisa diubah dari admin."""
	list_display = ('employee', 'claim_date', 'amount', 'approved_amount', 'status', 'decided_by')
	list_filter = ('status',)
	exclude = ('receipt',)                       # bukti hanya lewat unduhan yang diperiksa haknya

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False

	def has_delete_permission(self, request, obj=None):
		return False
