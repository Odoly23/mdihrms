"""Konfigurasaun absensia: tinan/fulan ativu, status absensia, feriadu nasionál, tolerânsia.
Hanya admin (ATTENDANCE_CONFIG_GROUPS). Mengaktifkan tinan/fulan lewat POST (bukan tautan GET) agar tidak bisa dipicu dari luar."""
from django.contrib import messages
from django.core.cache import cache
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from main import roles, ui

from . import qr_i18n as i18n
from .forms_config import AttendanceStatusForm, LOCKED_CODES, NacionalHolidayForm, ToleranceForm, YearForm
from .models import AttendanceStatus, Month, NacionalHoliday, Tolerance, Year

CONFIG = 'ATTENDANCE_CONFIG_GROUPS'


def _drop_holiday_cache():
	cache.delete('attqr:hol')                 # scan membaca daftar libur dari cache singkat


def _month_label(m, lang):
	return i18n.month_name(m.code, lang) if m.code and 1 <= m.code <= 12 else (m.name or '').strip()


@roles.role_required(CONFIG)
def dash(request):
	lang = ui.lang(request)
	months = list(Month.objects.order_by('code', 'id'))
	for m in months:
		m.label = _month_label(m, lang)
	return render(request, 'attendance/config/dash.html', {
		'title': ui.tr(lang, 'cfg.title'), 'years': Year.objects.order_by('-year'), 'months': months,
		'status': AttendanceStatus.objects.order_by('id'), 'locked': LOCKED_CODES,
		'year_form': YearForm(lang=lang)})


@require_POST
@roles.role_required(CONFIG)
def year_add(request):
	form = YearForm(request.POST, lang=ui.lang(request))
	if form.is_valid():
		form.save()
		messages.success(request, ui.tr(request, 'cfg.msg.saved'))
	else:
		for errs in form.errors.values():
			for e in errs:
				messages.error(request, e)
	return redirect('attendance-custom-dash')


@require_POST
@roles.role_required(CONFIG)
def year_set(request, pk):
	with transaction.atomic():
		y = get_object_or_404(Year.objects.select_for_update(), pk=pk)
		Year.objects.exclude(pk=pk).update(is_active=False)
		y.is_active = True
		y.save(update_fields=['is_active'])
	messages.success(request, ui.tr(request, 'cfg.msg.year_on', year=y.year))
	return redirect('attendance-custom-dash')


@require_POST
@roles.role_required(CONFIG)
def month_set(request, pk):
	with transaction.atomic():
		m = get_object_or_404(Month.objects.select_for_update(), pk=pk)
		Month.objects.exclude(pk=pk).update(is_active=False)
		m.is_active = True
		m.save(update_fields=['is_active'])
	messages.success(request, ui.tr(request, 'cfg.msg.month_on', month=_month_label(m, ui.lang(request))))
	return redirect('attendance-custom-dash')


def _form_page(request, form, title_key):
	return render(request, 'attendance/config/form.html', {'title': ui.tr(request, title_key), 'form': form})


@roles.role_required(CONFIG)
def status_add(request):
	form = AttendanceStatusForm(request.POST or None, lang=ui.lang(request))
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, ui.tr(request, 'cfg.msg.saved'))
		return redirect('attendance-custom-dash')
	return _form_page(request, form, 'cfg.status.add')


@roles.role_required(CONFIG)
def status_update(request, pk):
	obj = get_object_or_404(AttendanceStatus, pk=pk)
	form = AttendanceStatusForm(request.POST or None, instance=obj, lang=ui.lang(request))
	if request.method == 'POST' and form.is_valid():
		form.save()
		messages.success(request, ui.tr(request, 'cfg.msg.saved'))
		return redirect('attendance-custom-dash')
	return _form_page(request, form, 'cfg.status.edit')


@roles.role_required(CONFIG)
def holiday_list(request):
	return render(request, 'attendance/config/list.html', {
		'title': ui.tr(request, 'cfg.holiday'), 'objects': NacionalHoliday.objects.order_by('date'), 'kind': 'holiday',
		'add_url': 'attendance-custom-holiday-add', 'edit_url': 'attendance-custom-holiday-update'})


@roles.role_required(CONFIG)
def holiday_add(request):
	form = NacionalHolidayForm(request.POST or None, lang=ui.lang(request))
	if request.method == 'POST' and form.is_valid():
		form.save()
		_drop_holiday_cache()
		messages.success(request, ui.tr(request, 'cfg.msg.saved'))
		return redirect('attendance-custom-holiday-list')
	return _form_page(request, form, 'cfg.holiday.add')


@roles.role_required(CONFIG)
def holiday_update(request, pk):
	obj = get_object_or_404(NacionalHoliday, pk=pk)
	form = NacionalHolidayForm(request.POST or None, instance=obj, lang=ui.lang(request))
	if request.method == 'POST' and form.is_valid():
		form.save()
		_drop_holiday_cache()
		messages.success(request, ui.tr(request, 'cfg.msg.saved'))
		return redirect('attendance-custom-holiday-list')
	return _form_page(request, form, 'cfg.holiday.edit')


@roles.role_required(CONFIG)
def tolerance_list(request):
	y = Year.objects.filter(is_active=True).first()
	return render(request, 'attendance/config/list.html', {
		'title': ui.tr(request, 'cfg.tolerance.title', year=y or '-'), 'objects': Tolerance.objects.filter(year=y).order_by('date') if y else [],
		'kind': 'tolerance', 'y_active': y, 'add_url': 'attendance-custom-tolerance-add', 'edit_url': 'attendance-custom-tolerance-update'})


@roles.role_required(CONFIG)
def tolerance_add(request):
	y = Year.objects.filter(is_active=True).first()
	if y is None:
		messages.error(request, ui.tr(request, 'cfg.err.no_year'))
		return redirect('attendance-custom-dash')
	form = ToleranceForm(request.POST or None, year=y, lang=ui.lang(request))
	if request.method == 'POST' and form.is_valid():
		obj = form.save(commit=False)
		obj.year = y
		obj.save()
		_drop_holiday_cache()
		messages.success(request, ui.tr(request, 'cfg.msg.saved'))
		return redirect('attendance-custom-tolerance-list')
	return _form_page(request, form, 'cfg.tolerance.add')


@roles.role_required(CONFIG)
def tolerance_update(request, pk):
	obj = get_object_or_404(Tolerance, pk=pk)
	form = ToleranceForm(request.POST or None, instance=obj, year=obj.year, lang=ui.lang(request))
	if request.method == 'POST' and form.is_valid():
		form.save()
		_drop_holiday_cache()
		messages.success(request, ui.tr(request, 'cfg.msg.saved'))
		return redirect('attendance-custom-tolerance-list')
	return _form_page(request, form, 'cfg.tolerance.edit')
