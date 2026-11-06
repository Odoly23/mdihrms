import hashlib
import datetime

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from custom.models import DG, Department, Division, Section
from employee.models import Employee, EmployeeDivision, EmployeePosition
from main import roles

from .forms import PlacementForm
from .models import Kolokasaun

ACTIVE_STATUS = 1


def _employees(request):
	qs = (Employee.objects.filter(status_id=ACTIVE_STATUS)
		.select_related('employeedivision__dg', 'employeedivision__division', 'employeeposition__position')
		.order_by('first_name', 'last_name', 'id'))
	q = request.GET.get('q', '').strip()[:50]
	if q:
		qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q))
	div = request.GET.get('div', '')
	if div.isdigit():
		qs = qs.filter(employeedivision__division_id=int(div))
	return qs, q, div


@roles.role_required('PLACEMENT_VIEW_GROUPS')
def placement_list(request):
	qs, q, div = _employees(request)
	page = Paginator(qs, 50).get_page(request.GET.get('page'))
	return render(request, 'contract/placement_list.html', {
		'title': 'Kolokasaun', 'page': page, 'q': q, 'div': div, 'divisions': Division.objects.order_by('name'),
		'can_edit': roles.has_role(request.user, 'PLACEMENT_EDIT_GROUPS')})


@roles.role_required('PLACEMENT_VIEW_GROUPS')
def placement_history(request, emp_id):
	emp = get_object_or_404(Employee, pk=emp_id)
	rows = (Kolokasaun.objects.filter(employee=emp)
		.select_related('position', 'dg', 'division', 'department', 'section').order_by('-start_date', '-id'))
	return render(request, 'contract/placement_history.html', {
		'title': 'Istoria Kolokasaun', 'emp': emp, 'rows': rows,
		'can_edit': roles.has_role(request.user, 'PLACEMENT_EDIT_GROUPS')})


@roles.role_required('PLACEMENT_EDIT_GROUPS')
def placement_new(request, emp_id):
	emp = get_object_or_404(Employee, pk=emp_id, status_id=ACTIVE_STATUS)
	last = Kolokasaun.objects.filter(employee=emp, is_active=True).order_by('-start_date').first()
	cur_pos = EmployeePosition.objects.filter(employee=emp).first()
	cur_div = EmployeeDivision.objects.filter(employee=emp).first()
	initial = {'start_date': timezone.localdate()}
	if cur_pos:
		initial['position'] = cur_pos.position_id
	if cur_div:
		initial.update(dg=cur_div.dg_id, division=cur_div.division_id, department=cur_div.department_id,
			section=cur_div.section_id)
	form = PlacementForm(request.POST or None, initial=initial, last_start=last.start_date if last else None)
	if request.method == 'POST' and form.is_valid():
		d = form.cleaned_data
		with transaction.atomic():
			Employee.objects.select_for_update().get(pk=emp.pk)          # satu perubahan pada satu waktu
			prev = Kolokasaun.objects.filter(employee=emp, is_active=True)
			prev.update(is_active=False, end_date=d['start_date'] - datetime.timedelta(days=1))
			k = Kolokasaun.objects.create(
				employee=emp, position=d['position'], dg=d['dg'], division=d['division'], department=d['department'],
				section=d['section'], start_date=d['start_date'], is_active=True, is_confirm=True,
				disp_number=d['disp_number'] or None, datetime=timezone.now(), user=request.user)
			k.hashed = hashlib.md5(str(k.pk).encode()).hexdigest()
			k.save(update_fields=['hashed'])
			EmployeePosition.objects.update_or_create(employee=emp, defaults={'position': d['position']})
			EmployeeDivision.objects.update_or_create(employee=emp, defaults={
				'dg': d['dg'], 'division': d['division'], 'department': d['department'], 'section': d['section']})
		messages.success(request, "Kolokasaun foun rai ona.")
		return redirect('placement-history', emp_id=emp.pk)
	return render(request, 'contract/placement_form.html', {
		'title': 'Kolokasaun Foun', 'emp': emp, 'form': form,
		'divisions': list(Division.objects.values('id', 'dg_id')), 'departments': list(Department.objects.values('id', 'division_id')),
		'sections': list(Section.objects.values('id', 'department_id'))})
