from django.contrib import admin

from .models import AnnualLeaves, LeaveNotes, Leaves, LeaveType

for m in (LeaveType, LeaveNotes, Leaves, AnnualLeaves):
	admin.site.register(m)
