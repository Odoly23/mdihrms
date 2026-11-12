import datetime
import hashlib

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from attendance import qr_service as svc
from main import roles, ui

from . import services
from .forms import ClaimForm
from .models import HealthClaim, STATUSES

REQUEST, APPROVER, VIEW_ALL, PAYER = 'HEALTH_REQUEST_GROUPS', 'HEALTH_APPROVER_GROUPS', 'HEALTH_VIEW_ALL_GROUPS', 'HEALTH_PAYER_GROUPS'
BADGE = {'pending': 'warning', 'approved': 'info', 'rejected': 'danger', 'paid': 'success'}


def _fail(request, exc):
	messages.error(request, ui.tr(request, exc.key, **exc.params))


def _decorate(claims, lang):
	for c in claims:
		c.status_text, c.badge = ui.tr(lang, 'hl.st.' + c.status), BADGE.get(c.status, 'secondary')
	return claims


def _today():
	return svc.to_local(timezone.now()).date()


@roles.role_required(REQUEST)
def my_claims(request):
	lang = ui.lang(request)
	emp = roles.linked_employee(request.user)
	claims = list(HealthClaim.objects.filter(employee=emp).order_by('-claim_date', '-id')[:100]) if emp else []
	return render(request, 'health/list.html', {
		'title': ui.tr(lang, 'hl.title.mine'), 'rows': _decorate(claims, lang), 'mode': 'mine', 'emp': emp, 'bonus': services.bonus_amount(),
		'summary': services.year_summary(emp, _today().year) if emp else None})


@roles.role_required(REQUEST)
def claim_new(request):
	lang = ui.lang(request)
	emp = roles.linked_employee(request.user)
	if not emp:
		messages.error(request, ui.tr(lang, 'leave.msg.unlinked'))
		return redirect('health-mine')
	form = ClaimForm(request.POST or None, request.FILES or None, employee=emp, lang=lang, today=_today())
	if request.method == 'POST' and form.is_valid():
		c = form.save(commit=False)
		c.employee, c.status, c.user = emp, 'pending', request.user
		c.save()
		messages.success(request, ui.tr(lang, 'hl.msg.sent'))
		return redirect('health-mine')
	return render(request, 'health/form.html', {'title': ui.tr(lang, 'hl.new'), 'form': form, 'bonus': services.bonus_amount()})


@require_POST
@roles.role_required(REQUEST)
def claim_cancel(request, pk):
	emp = roles.linked_employee(request.user)
	if emp is None:
		return redirect('health-mine')
	get_object_or_404(HealthClaim, pk=pk, employee=emp)
	try:
		services.cancel(pk, emp)
		messages.success(request, ui.tr(request, 'hl.msg.canceled'))
	except services.ClaimError as e:
		_fail(request, e)
	return redirect('health-mine')


@roles.role_required(VIEW_ALL)
def all_claims(request):
	lang = ui.lang(request)
	status = request.GET.get('status', 'pending')
	qs = HealthClaim.objects.select_related('employee').order_by('-claim_date', '-id')
	if status in STATUSES:
		qs = qs.filter(status=status)
	q = request.GET.get('q', '').strip()[:50]
	if q:
		qs = qs.filter(Q(employee__first_name__icontains=q) | Q(employee__last_name__icontains=q))
	page = Paginator(qs, 50).get_page(request.GET.get('page'))
	mine = roles.linked_employee(request.user)
	return render(request, 'health/list.html', {
		'title': ui.tr(lang, 'hl.title.all'), 'rows': _decorate(list(page.object_list), lang), 'page': page, 'mode': 'all', 'status': status, 'q': q,
		'can_decide': roles.has_role(request.user, APPROVER), 'can_pay': roles.has_role(request.user, PAYER), 'mine_id': mine.pk if mine else None, 'limit': services.annual_limit(),
		'status_choices': [('pending', 'hl.st.pending'), ('approved', 'hl.st.approved'), ('paid', 'hl.st.paid'), ('rejected', 'hl.st.rejected'), ('all', 'leave.f.all')]})


@require_POST
@roles.role_required(APPROVER)
def claim_decide(request, pk, action):
	if action not in ('approve', 'reject'):
		return redirect('health-all')
	get_object_or_404(HealthClaim, pk=pk)
	try:
		services.decide(pk, action == 'approve', request.user, request.POST.get('note', ''),
			approver_employee=roles.linked_employee(request.user))
		messages.success(request, ui.tr(request, 'hl.msg.approved' if action == 'approve' else 'hl.msg.rejected'))
	except services.ClaimError as e:
		_fail(request, e)
	return redirect('health-all')


@require_POST
@roles.role_required(PAYER)
def claim_pay(request, pk):
	get_object_or_404(HealthClaim, pk=pk)
	try:
		services.mark_paid(pk, request.user)
		messages.success(request, ui.tr(request, 'hl.msg.paid'))
	except services.ClaimError as e:
		_fail(request, e)
	return redirect('health-all')


@require_GET
def receipt(request, pk):
	"""Bukti hanya untuk pemilik klaim dan peran yang boleh melihat semua; diunduh sebagai lampiran (tidak dieksekusi browser)."""
	from django.contrib.auth.views import redirect_to_login
	if not request.user.is_authenticated:
		return redirect_to_login(request.get_full_path())
	c = get_object_or_404(HealthClaim.objects.select_related('employee'), pk=pk)
	mine = roles.linked_employee(request.user)
	if not (roles.has_role(request.user, VIEW_ALL) or (mine and c.employee_id == mine.pk)):
		return render(request, 'home/403.html', status=403)
	try:
		f = c.receipt.open('rb')
	except (FileNotFoundError, ValueError):
		raise Http404
	resp = FileResponse(f, as_attachment=True, filename='health-%d.%s' % (c.pk, c.receipt.name.rsplit('.', 1)[-1]))
	resp['X-Content-Type-Options'] = 'nosniff'
	resp['Cache-Control'] = 'private, no-store'
	return resp
