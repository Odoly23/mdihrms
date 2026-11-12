import csv

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from attendance import qr_service as svc
from main import roles, ui

from . import services
from .forms import AssetForm, AssignForm, ReturnForm, StatusForm, category_name
from .models import Asset, AssetCategory, AssetEvent, STATUSES

BADGE = {'new': 'info', 'in_use': 'success', 'returned': 'secondary', 'in_repair': 'warning', 'broken': 'danger', 'in_stock': 'primary'}
MANAGE, VIEW_ALL, SELF = 'ASSET_MANAGER_GROUPS', 'ASSET_VIEW_ALL_GROUPS', 'ASSET_SELF_GROUPS'


def _fail(request, exc):
	messages.error(request, ui.tr(request, exc.key, **exc.params))


def _decorate(assets, lang):
	for a in assets:
		a.status_text, a.badge = ui.tr(lang, 'ast.' + a.status), BADGE.get(a.status, 'secondary')
		a.category_text = category_name(a.category, lang)
	return assets


def _filtered(request):
	qs = Asset.objects.filter(is_active=True).select_related('category', 'holder')
	q = request.GET.get('q', '').strip()[:60]
	if q:
		qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q) | Q(serial_number__icontains=q) | Q(brand__icontains=q) |
			Q(model__icontains=q) | Q(shelf__icontains=q) | Q(holder__first_name__icontains=q) | Q(holder__last_name__icontains=q))
	cat = request.GET.get('category', '')
	if cat.isdigit() and int(cat) < 2 ** 31:
		qs = qs.filter(category_id=int(cat))
	where = request.GET.get('where', '')
	if where == 'stock':
		qs = qs.filter(holder__isnull=True)
	elif where == 'held':
		qs = qs.filter(holder__isnull=False)
	return qs, q, cat, where


@roles.role_required(VIEW_ALL)
def asset_list(request):
	lang = ui.lang(request)
	qs, q, cat, where = _filtered(request)
	counts = {r['status']: r['n'] for r in qs.values('status').annotate(n=Count('id'))}
	status = request.GET.get('status', '')
	if status in STATUSES:
		qs = qs.filter(status=status)
	page = Paginator(qs.order_by('code'), 50).get_page(request.GET.get('page'))
	_decorate(page.object_list, lang)
	return render(request, 'assets/list.html', {
		'title': ui.tr(lang, 'as.title'), 'page': page, 'q': q, 'cat': cat, 'where': where, 'status': status,
		'tiles': [{'code': s, 'n': counts.get(s, 0), 'text': ui.tr(lang, 'ast.' + s), 'badge': BADGE[s]} for s in STATUSES],
		'categories': [(c.pk, category_name(c, lang)) for c in AssetCategory.objects.order_by('name')],
		'can_manage': roles.has_role(request.user, MANAGE)})


@roles.role_required(MANAGE)
def asset_add(request):
	lang = ui.lang(request)
	form = AssetForm(request.POST or None, lang=lang)
	if request.method == 'POST' and form.is_valid():
		a = form.save(commit=False)
		a.status = form.cleaned_data.get('status') or 'new'
		a.shelf = (form.cleaned_data.get('shelf') or '').strip() if a.status == 'in_stock' else ''
		try:
			services.create(a, request.user)
		except services.AssetError as e:
			_fail(request, e)
		else:
			messages.success(request, ui.tr(request, 'as.msg.added'))
			return redirect('asset-detail', pk=a.pk)
	return render(request, 'assets/form.html', {'title': ui.tr(lang, 'as.add'), 'form': form})


@roles.role_required(MANAGE)
def asset_edit(request, pk):
	a = get_object_or_404(Asset, pk=pk)
	form = AssetForm(request.POST or None, instance=a, lang=ui.lang(request))
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, ui.tr(request, 'as.msg.saved'))
		return redirect('asset-detail', pk=a.pk)
	return render(request, 'assets/form.html', {'title': ui.tr(request, 'as.edit'), 'form': form, 'asset': a})


def _mine(request):
	return roles.linked_employee(request.user)


def asset_detail(request, pk):
	from django.contrib.auth.views import redirect_to_login
	if not request.user.is_authenticated:
		return redirect_to_login(request.get_full_path())
	a = get_object_or_404(Asset.objects.select_related('category', 'holder'), pk=pk)
	mine = _mine(request)
	can_all = roles.has_role(request.user, VIEW_ALL)
	if not can_all and not (mine and a.holder_id == mine.pk):
		return render(request, 'home/403.html', status=403)
	lang = ui.lang(request)
	_decorate([a], lang)
	events = list(AssetEvent.objects.filter(asset=a).select_related('employee', 'user')[:60])
	for ev in events:
		ev.kind_text = ui.tr(lang, 'ev.' + ev.kind)
		ev.from_text = ui.tr(lang, 'ast.' + ev.from_status) if ev.from_status else ''
		ev.to_text = ui.tr(lang, 'ast.' + ev.to_status) if ev.to_status else ''
	manage = roles.has_role(request.user, MANAGE)
	ctx = {'title': a.code, 'asset': a, 'events': events, 'can_manage': manage, 'is_holder': bool(mine and a.holder_id == mine.pk)}
	if manage:
		ctx.update(assign_form=AssignForm(lang=lang), return_form=ReturnForm(lang=lang), status_form=StatusForm(lang=lang))
	return render(request, 'assets/detail.html', ctx)


def _action(view):
	"""POST-only, hanya pengelola; hasil kembali ke halaman barang."""
	@require_POST
	@roles.role_required(MANAGE)
	def inner(request, pk):
		get_object_or_404(Asset, pk=pk)
		try:
			view(request, pk)
		except services.AssetError as e:
			_fail(request, e)
		return redirect('asset-detail', pk=pk)
	inner.__name__ = view.__name__
	return inner


@_action
def action_assign(request, pk):
	form = AssignForm(request.POST, lang=ui.lang(request))
	if not form.is_valid():
		messages.error(request, ui.tr(request, 'as.err.form'))
		return
	services.assign(pk, form.cleaned_data['employee'], request.user, form.cleaned_data['note'])
	messages.success(request, ui.tr(request, 'as.msg.assigned'))


@_action
def action_return(request, pk):
	form = ReturnForm(request.POST, lang=ui.lang(request))
	if not form.is_valid():
		messages.error(request, ui.tr(request, 'as.err.form'))
		return
	d = form.cleaned_data
	services.return_asset(pk, request.user, d['to_status'], d['shelf'], d['note'])
	messages.success(request, ui.tr(request, 'as.msg.returned'))


@_action
def action_status(request, pk):
	form = StatusForm(request.POST, lang=ui.lang(request))
	if not form.is_valid():
		messages.error(request, ui.tr(request, 'as.err.form'))
		return
	d = form.cleaned_data
	services.set_status(pk, d['to_status'], request.user, d['shelf'], d['note'])
	messages.success(request, ui.tr(request, 'as.msg.status'))


@_action
def action_shelf(request, pk):
	services.move_shelf(pk, request.POST.get('shelf', ''), request.user, request.POST.get('note', ''))
	messages.success(request, ui.tr(request, 'as.msg.shelf'))


@_action
def action_confirm(request, pk):
	services.confirm(pk, request.user, request.POST.get('note', ''))
	messages.success(request, ui.tr(request, 'as.msg.confirmed'))


@roles.role_required(SELF)
def my_assets(request):
	lang = ui.lang(request)
	emp = _mine(request)
	items = list(Asset.objects.filter(holder=emp, is_active=True).select_related('category').order_by('code')) if emp else []
	_decorate(items, lang)
	return render(request, 'assets/mine.html', {'title': ui.tr(lang, 'as.mine'), 'items': items, 'emp': emp})


def _self(view):
	@require_POST
	@roles.role_required(SELF)
	def inner(request, pk):
		emp = _mine(request)
		if emp is None:
			messages.error(request, ui.tr(request, 'leave.msg.unlinked'))
			return redirect('asset-mine')
		try:
			view(request, pk, emp)
		except services.AssetError as e:
			_fail(request, e)
		return redirect('asset-mine')
	inner.__name__ = view.__name__
	return inner


@_self
def self_status(request, pk, emp):
	services.set_status(pk, request.POST.get('to_status', ''), request.user, note=request.POST.get('note', ''), self_service_for=emp)
	messages.success(request, ui.tr(request, 'as.msg.reported'))


@_self
def self_confirm(request, pk, emp):
	services.confirm(pk, request.user, request.POST.get('note', ''), self_service_for=emp)
	messages.success(request, ui.tr(request, 'as.msg.confirmed'))


@roles.role_required(VIEW_ALL)
def survey(request):
	lang = ui.lang(request)
	s = services.summary()
	for r in s['rows']:
		r['name'] = category_name(r['category'], lang)
	s['attention'] = _decorate(list(s['attention']), lang)
	return render(request, 'assets/survey.html', {
		'title': ui.tr(lang, 'as.survey'), 's': s,
		'cols': [{'code': c, 'text': ui.tr(lang, 'ast.' + c), 'badge': BADGE[c], 'total': s['totals'][c]} for c in STATUSES]})


@roles.role_required(VIEW_ALL)
def survey_csv(request):
	lang = ui.lang(request)
	resp = HttpResponse(content_type='text/csv; charset=utf-8')
	resp['Content-Disposition'] = 'attachment; filename="assets-survey-%s.csv"' % svc.to_local(timezone.now()).date().isoformat()
	resp.write('﻿')
	w = csv.writer(resp)
	w.writerow([ui.tr(lang, h) for h in ('th.code', 'th.name', 'as.f.category', 'th.status', 'th.emp', 'as.f.shelf', 'as.f.serial', 'as.last_checked')])
	for a in Asset.objects.filter(is_active=True).select_related('category', 'holder').order_by('category__name', 'code').iterator():
		w.writerow([ui.csv_safe(x) for x in (a.code, a.name, category_name(a.category, lang), ui.tr(lang, 'ast.' + a.status),
			str(a.holder) if a.holder_id else '', a.shelf, a.serial_number,
			svc.to_local(a.last_checked).strftime('%Y-%m-%d') if a.last_checked else '')])
	return resp
