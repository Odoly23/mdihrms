import datetime
import hashlib

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from main import roles, ui

from .forms import LeaveRequestForm
from .models import Leaves

STATUS = {'pending': ('leave.st.pending', 'warning'), 'approved': ('leave.st.approved', 'success'),
	'rejected': ('leave.st.rejected', 'danger')}


def leave_state(lv):
	if lv.is_confirm:
		return 'approved'
	if lv.is_active:
		return 'pending'
	return 'rejected'


def _rows(qs, lang='tet'):
	out = []
	for lv in qs:
		code = leave_state(lv)
		key, lv.state_class = STATUS[code]
		lv.state, lv.state_text = code, ui.tr(lang, key)
		lv.days = (lv.end_date - lv.start_date).days + 1
		out.append(lv)
	return out


@roles.role_required('LEAVE_REQUEST_GROUPS')
def my_list(request):
	emp = roles.linked_employee(request.user)
	qs = Leaves.objects.filter(employee=emp).select_related('leave_type').order_by('-start_date', '-id')[:100] if emp else []
	return render(request, 'leave/list.html', {'title': ui.tr(request, 'leave.title.mine'), 'rows': _rows(qs, ui.lang(request)),
		'emp': emp, 'mode': 'mine'})


@roles.role_required('LEAVE_REQUEST_GROUPS')
def new(request):
	emp = roles.linked_employee(request.user)
	if not emp:
		messages.error(request, ui.tr(request, 'leave.msg.unlinked'))
		return redirect('leave-mine')
	form = LeaveRequestForm(request.POST or None, request.FILES or None, employee=emp, lang=ui.lang(request))
	if request.method == 'POST' and form.is_valid():
		d = form.cleaned_data
		with transaction.atomic():
			lv = Leaves.objects.create(
				employee=emp, leave_type=d['leave_type'], start_date=d['start_date'], end_date=d['end_date'],
				is_active=True, is_confirm=False, user=request.user)
			lv.hashed = hashlib.md5(str(lv.pk).encode()).hexdigest()
			if d.get('file'):
				lv.file = d['file']
			lv.save()
		messages.success(request, ui.tr(request, 'leave.msg.sent'))
		return redirect('leave-mine')
	return render(request, 'leave/form.html', {'title': ui.tr(request, 'leave.title.new'), 'form': form})


@require_POST
@roles.role_required('LEAVE_REQUEST_GROUPS')
def cancel(request, pk):
	emp = roles.linked_employee(request.user)
	lv = get_object_or_404(Leaves, pk=pk, employee=emp) if emp else None
	if lv is None:
		return redirect('leave-mine')
	if leave_state(lv) == 'pending':
		lv.is_active = False
		lv.save(update_fields=['is_active'])
		messages.success(request, ui.tr(request, 'leave.msg.canceled'))
	return redirect('leave-mine')


@roles.role_required('LEAVE_VIEW_ALL_GROUPS')
def all_list(request):
	status = request.GET.get('status', 'pending')
	qs = Leaves.objects.select_related('employee', 'leave_type').order_by('-start_date', '-id')
	if status == 'pending':
		qs = qs.filter(is_active=True, is_confirm=False)
	elif status == 'approved':
		qs = qs.filter(is_confirm=True)
	elif status == 'rejected':
		qs = qs.filter(is_active=False, is_confirm=False)
	q = request.GET.get('q', '').strip()[:50]
	if q:
		qs = qs.filter(Q(employee__first_name__icontains=q) | Q(employee__last_name__icontains=q))
	mine = roles.linked_employee(request.user)
	return render(request, 'leave/list.html', {
		'title': ui.tr(request, 'leave.title.all'), 'rows': _rows(qs[:200], ui.lang(request)), 'mode': 'all', 'status': status, 'q': q,
		'can_decide': roles.has_role(request.user, 'LEAVE_APPROVER_GROUPS'), 'mine_id': mine.pk if mine else None})


@require_POST
@roles.role_required('LEAVE_APPROVER_GROUPS')
def decide(request, pk, action):
	if action not in ('approve', 'reject'):
		return redirect('leave-all')
	with transaction.atomic():
		lv = get_object_or_404(Leaves.objects.select_for_update(), pk=pk)
		mine = roles.linked_employee(request.user)
		if mine and lv.employee_id == mine.pk:
			messages.error(request, ui.tr(request, 'leave.msg.self'))
		elif leave_state(lv) != 'pending':
			messages.warning(request, ui.tr(request, 'leave.msg.done'))
		elif action == 'approve':
			lv.is_confirm = True
			lv.save(update_fields=['is_confirm'])
			messages.success(request, ui.tr(request, 'leave.msg.approved'))
		else:
			lv.is_active = False
			lv.save(update_fields=['is_active'])
			messages.success(request, ui.tr(request, 'leave.msg.rejected'))
	return redirect('leave-all')
