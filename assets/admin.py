from django.contrib import admin

from .models import Asset, AssetCategory, AssetEvent


@admin.register(AssetCategory)
class CategoryAdmin(admin.ModelAdmin):
	list_display = ('name', 'code')


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
	list_display = ('code', 'name', 'category', 'status', 'holder', 'shelf', 'is_active')
	list_filter = ('status', 'category', 'is_active')
	search_fields = ('code', 'name', 'serial_number')
	raw_id_fields = ('holder', 'user')


@admin.register(AssetEvent)
class EventAdmin(admin.ModelAdmin):
	list_display = ('at', 'asset', 'kind', 'from_status', 'to_status', 'employee', 'user')
	raw_id_fields = ('asset', 'employee', 'user')

	def has_change_permission(self, request, obj=None):          # riwayat tidak boleh diubah
		return False

	def has_delete_permission(self, request, obj=None):
		return False
