from django.contrib import admin

from .models import HealthClaim


@admin.register(HealthClaim)
class ClaimAdmin(admin.ModelAdmin):
	list_display = ('employee', 'claim_date', 'amount', 'approved_amount', 'status')
	list_filter = ('status',)
	raw_id_fields = ('employee', 'leave', 'decided_by', 'user')
	exclude = ('receipt',)                       # bukti tidak ditampilkan di admin (hanya lewat unduhan yang diperiksa haknya)
