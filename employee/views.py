import datetime

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.utils import timezone

from attendance import qr_service as svc
from contract.models import Kolokasaun
from custom.models import Division
from leave.models import Leaves
from leave.views import _rows as leave_rows
from main import groups, roles, ui

from .models import Employee, EmployeeUser

ACTIVE_STATUS = 1


@roles.role_required('DIRECTORY_GROUPS')
def staff_list(request):
	"""Daftar funsionariu aktif: cari nama, saring per program (diresaun) dan grup."""
	qs = (Employee.objects.filter(status_id=ACTIVE_STATUS)
		.select_related('employeedivision__division', 'employeeposition__position', 'idfnumber')
		.order_by('first_name', 'last_name', 'id'))
	q = request.GET.get('q', '').strip()[:50]
	if q:
		qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(idfnumber__nrf__icontains=q))
	div = request.GET.get('div', '')
	if div.isdigit():
		qs = qs.filter(employeedivision__division_id=int(div))
	grp = request.GET.get('grp', '')
	if grp in groups.GROUPS:
		qs = qs.filter(employeeuser__user__groups__name=grp)
	elif grp == 'none':
		qs = qs.exclude(employeeuser__user__groups__name__in=groups.GROUPS)           # belum punya akun/grup
	page = Paginator(qs, 50).get_page(request.GET.get('page'))
	gmap, accounts = {}, {}
	for eu in EmployeeUser.objects.filter(employee__in=list(page)).prefetch_related('user__groups'):
		gmap[eu.employee_id] = [g.name for g in eu.user.groups.all() if g.name in groups.GROUPS]
		accounts[eu.employee_id] = eu.user_id
	for e in page:
		e.group_names = gmap.get(e.pk, [])
		e.account_id = accounts.get(e.pk)
		e.can_reset = bool(e.account_id) and e.account_id != request.user.pk      # akunnya sendiri: pakai Ganti kata sandi
	return render(request, 'employee/staff_list.html', {
		'title': ui.tr(request, 'staff.title'), 'page': page, 'q': q, 'div': div, 'grp': grp, 'group_choices': groups.GROUPS,
		'divisions': Division.objects.order_by('name')})


@roles.role_required('DIRECTORY_GROUPS')
def staff_detail(request, emp_id):
	emp = get_object_or_404(
		Employee.objects.select_related('employeedivision__division', 'employeeposition__position',
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

from .forms import AddressForm, EmployeeForm  # noqa: E402
from .models import LocationTL  # noqa: E402
from .services import save_address, save_employee  # noqa: E402


def _hier():
	return {}


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


@roles.role_required('EMPLOYEE_EDIT_GROUPS')
@require_POST
def staff_reset_password(request, emp_id):
	"""Admin sistem mereset kata sandi akun pegawai ke kata sandi awal; pengguna wajib menggantinya saat login berikutnya."""
	from django.conf import settings
	from django.contrib.admin.models import CHANGE, LogEntry
	from django.contrib.auth.models import User
	from django.contrib.contenttypes.models import ContentType
	from django.db import transaction
	from main import middleware
	from main.models import MustChangePassword
	lang = ui.lang(request)
	link = EmployeeUser.objects.select_related('user', 'employee').filter(employee_id=emp_id).first()
	if link is None:
		messages.error(request, ui.tr(lang, 'rst.none'))
	elif link.user_id == request.user.pk:
		messages.error(request, ui.tr(lang, 'rst.self'))
	else:
		with transaction.atomic():
			u = link.user
			u.set_password(settings.MDI_DEFAULT_PASSWORD)                  # sesi lama akun itu otomatis tidak berlaku lagi
			u.save(update_fields=['password'])
			MustChangePassword.objects.update_or_create(user=u, defaults={'by': request.user})
			middleware.set_flag(u.pk, True)
			LogEntry.objects.log_action(request.user.pk, ContentType.objects.get_for_model(User).pk, u.pk, str(u), CHANGE, 'password reset to default')
		messages.success(request, ui.tr(lang, 'rst.done', name=str(link.employee), user=link.user.username))
	return redirect(request.META.get('HTTP_REFERER') if _same_site(request) else 'staff-list')


def _same_site(request):
	from django.utils.http import url_has_allowed_host_and_scheme
	ref = request.META.get('HTTP_REFERER')
	return bool(ref) and url_has_allowed_host_and_scheme(ref, {request.get_host()}, require_https=request.is_secure())
