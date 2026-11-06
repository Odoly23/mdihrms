from django.contrib import admin

from .models import (Attendance, AttendanceDiv, AttendanceStatus, AttendanceTime, Leave, Month, NacionalHoliday,
	OfficeNetwork, OverTime, QRCard, ScanDevice, ScanLog, Tolerance, Year)

for m in (AttendanceStatus, AttendanceDiv, Leave, OverTime, Year, Month, NacionalHoliday, Tolerance, QRCard,
		OfficeNetwork):
	admin.site.register(m)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
	list_display = ('employee', 'date', 'status_am', 'status_pm')
	list_filter = ('date',)
	raw_id_fields = ('employee', 'user')


@admin.register(AttendanceTime)
class AttendanceTimeAdmin(admin.ModelAdmin):
	list_display = ('attendance', 'check_in', 'check_out', 'is_late', 'flagged')
	list_filter = ('flagged', 'is_late')
	raw_id_fields = ('attendance', 'device')


@admin.register(ScanDevice)
class ScanDeviceAdmin(admin.ModelAdmin):
	list_display = ('name', 'is_active', 'last_seen')
	exclude = ('key_sha256', 'prev_sha256')


@admin.register(ScanLog)
class ScanLogAdmin(admin.ModelAdmin):
	list_display = ('scanned_at', 'code', 'employee', 'device', 'ip', 'flag')
	list_filter = ('code', 'flag')
	raw_id_fields = ('employee', 'device')
