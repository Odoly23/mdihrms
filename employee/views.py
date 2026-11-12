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
from main import roles, ui

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
		'title': ui.tr(request, 'staff.title'), 'page': page, 'q': q, 'dg': dg, 'div': div,
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
	leaves = leave_rows(Leaves.objects.filter(employee=emp).select_related('leave_type').order_by('-start_date')[:10], ui.lang(request))
	places = Kolokasaun.objects.filter(employee=emp).select_related('position', 'division').order_by('-start_date')[:10]
	held = []
	if roles.has_role(request.user, 'ASSET_VIEW_ALL_GROUPS'):
		from assets.models import Asset
		held = list(Asset.objects.filter(holder=emp, is_active=True).select_related('category').order_by('code'))
		for a in held:
			a.status_text = ui.tr(ui.lang(request), 'ast.' + a.status)
	return render(request, 'employee/staff_detail.html', {'held_assets': held, 
		'title': str(emp), 'emp': emp, 'row': row, 'month': today.month, 'year': today.year, 'leaves': leaves, 'places': places,
		'can_edit_place': roles.has_role(request.user, 'PLACEMENT_EDIT_GROUPS')})


# ----------------------------------------------------------------- tambah / ubah funsionariu (hanya admin)
from django.contrib import messages  # noqa: E402
from django.shortcuts import redirect  # noqa: E402

from custom.models import Department, Section  # noqa: E402

from .forms import AddressForm, EmployeeForm  # noqa: E402
from .models import LocationTL  # noqa: E402
from .services import save_address, save_employee  # noqa: E402


def _hier():
	return {'divisions': list(Division.objects.values('id', 'dg_id')),
		'departments': list(Department.objects.values('id', 'division_id')),
		'sections': list(Section.objects.values('id', 'department_id'))}


@roles.role_required('EMPLOYEE_EDIT_GROUPS')
def employee_add(request):
	form = EmployeeForm(request.POST or None, request.FILES or None, lang=ui.lang(request))
	if request.method == 'POST' and form.is_valid():
		emp, account = save_employee(form, request.user, form.cleaned_data.get('create_account'))
		messages.success(request, ui.tr(request, 'emp.msg.added'))
		if account:
			messages.warning(request, ui.tr(request, 'emp.msg.account', user=account[0], pwd=account[1]))
		return redirect('staff-detail', emp_id=emp.pk)
	return render(request, 'employee/form.html', dict(_hier(), title=ui.tr(request, 'emp.add'), form=form, mode='employee'))


@roles.role_required('EMPLOYEE_EDIT_GROUPS')
def employee_edit(request, emp_id):
	emp = get_object_or_404(Employee, pk=emp_id)
	form = EmployeeForm(request.POST or None, request.FILES or None, instance=emp, lang=ui.lang(request))
	if request.method == 'POST' and form.is_valid():
		save_employee(form, request.user)
		messages.success(request, ui.tr(request, 'emp.msg.updated'))
		return redirect('staff-detail', emp_id=emp.pk)
	return render(request, 'employee/form.html', dict(_hier(), title=ui.tr(request, 'emp.edit'), form=form, mode='employee', emp=emp))


@roles.role_required('EMPLOYEE_EDIT_GROUPS')
def employee_address(request, emp_id):
	emp = get_object_or_404(Employee, pk=emp_id)
	loc = LocationTL.objects.filter(employee=emp).first()
	initial = {'municipality': loc.municipality_id, 'administrativepost': loc.administrativepost_id,
		'village': loc.village_id, 'aldeia': loc.aldeia} if loc else {}
	form = AddressForm(request.POST or None, initial=initial, lang=ui.lang(request))
	if request.method == 'POST' and form.is_valid():
		save_address(emp, form, request.user)
		messages.success(request, ui.tr(request, 'emp.msg.addr'))
		return redirect('staff-detail', emp_id=emp.pk)
	return render(request, 'employee/form.html', {'title': ui.tr(request, 'emp.address'), 'form': form, 'mode': 'address', 'emp': emp})
