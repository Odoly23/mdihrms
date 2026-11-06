import datetime

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from attendance import qr_service as svc
from contract.models import Kolokasaun
from custom.models import DG, Division
from leave.models import Leaves
from leave.views import _rows as leave_rows
from main import roles

from .models import Employee

ACTIVE_STATUS = 1


@roles.role_required('DIRECTORY_GROUPS')
def staff_list(request):
	"""Daftar funsionariu aktif: cari nama, saring per diresaun geral / diresaun."""
	qs = (Employee.objects.filter(status_id=ACTIVE_STATUS)
		.select_related('employeedivision__dg', 'employeedivision__division', 'employeeposition__position', 'idfnumber')
		.order_by('first_name', 'last_name', 'id'))
	q = request.GET.get('q', '').strip()[:50]
	if q:
		qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(idfnumber__nrf__icontains=q))
	dg, div = request.GET.get('dg', ''), request.GET.get('div', '')
	if dg.isdigit():
		qs = qs.filter(employeedivision__dg_id=int(dg))
	if div.isdigit():
		qs = qs.filter(employeedivision__division_id=int(div))
	page = Paginator(qs, 50).get_page(request.GET.get('page'))
	return render(request, 'employee/staff_list.html', {
		'title': 'Funsionariu', 'page': page, 'q': q, 'dg': dg, 'div': div,
		'dgs': DG.objects.order_by('name'), 'divisions': Division.objects.order_by('name')})


@roles.role_required('DIRECTORY_GROUPS')
def staff_detail(request, emp_id):
	emp = get_object_or_404(
		Employee.objects.select_related('employeedivision__dg', 'employeedivision__division',
			'employeedivision__department', 'employeedivision__section', 'employeeposition__position',
			'idfnumber', 'contactinfo'), pk=emp_id)
	today = svc.to_local(timezone.now()).date()
	rep = svc.month_report(today.year, today.month, employee=emp)
	row = rep['rows'][0] if rep['rows'] else None
	leaves = leave_rows(Leaves.objects.filter(employee=emp).select_related('leave_type').order_by('-start_date')[:10])
	places = Kolokasaun.objects.filter(employee=emp).select_related('position', 'division').order_by('-start_date')[:10]
	return render(request, 'employee/staff_detail.html', {
		'title': str(emp), 'emp': emp, 'row': row, 'month': today.month, 'year': today.year, 'leaves': leaves, 'places': places,
		'can_edit_place': roles.has_role(request.user, 'PLACEMENT_EDIT_GROUPS')})
