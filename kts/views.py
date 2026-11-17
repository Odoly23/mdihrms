import datetime

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
from .forms import DisposeForm, DoneForm, SaiForm, TamaForm
from .models import STATUSES, Sai, Tama, TamaEvent

REGISTER, VERIFY, DISPOSE, VIEW_ALL, OUT = ('KTS_REGISTER_GROUPS', 'KTS_VERIFY_GROUPS', 'KTS_DISPOSE_GROUPS', 'KTS_VIEW_ALL_GROUPS', 'KTS_OUT_GROUPS')
BADGE = {'registered': 'warning', 'returned': 'danger', 'approved': 'info', 'disposed': 'primary', 'done': 'success'}


def _today():
	return svc.to_local(timezone.now()).date()


def _mine(request):
	return roles.linked_employee(request.user)


def _fail(request, exc):
	messages.error(request, ui.tr(request, exc.key, **exc.params))


def _decorate(rows, lang):
	for r in rows:
		r.status_text, r.badge = ui.tr(lang, 'kts.st.' + r.status), BADGE.get(r.status, 'secondary')
	return rows


def _involved(request):
	"""Boleh membuka dasbor: punya peran surat atau menjadi penanggung jawab."""
	u = request.user
	return any(roles.has_role(u, k) for k in (REGISTER, VERIFY, DISPOSE, VIEW_ALL, OUT)) or (
		_mine(request) is not None and Tama.objects.filter(handler=_mine(request)).exists())


def _guard(request):
	from django.contrib.auth.views import redirect_to_login
	if not request.user.is_authenticated:
		return redirect_to_login(request.get_full_path())
	return None


def dash(request):
	r = _guard(request)
	if r:
		return r
	if not _involved(request):
		return render(request, 'home/403.html', status=403)
	lang = ui.lang(request)
	mine = _mine(request)
	counts = services.counts_for(request.user, mine, roles)
	return render(request, 'kts/dash.html', {
		'title': ui.tr(lang, 'kts.title'), 'counts': counts,
		'can_all': roles.has_role(request.user, VIEW_ALL), 'can_out': roles.has_role(request.user, OUT),
		'can_register': roles.has_role(request.user, REGISTER), 'has_handled': mine is not None and Tama.objects.filter(handler=mine).exists()})


# ------------------------------------------------------------------ surat masuk
@roles.role_required(VIEW_ALL)
def tama_list(request):
	lang = ui.lang(request)
	qs = Tama.objects.select_related('handler', 'institutu')
	status = request.GET.get('status', '')
	if status in STATUSES:
		qs = qs.filter(status=status)
	year = request.GET.get('year', '')
	if year.isdigit() and len(year) == 4:
		qs = qs.filter(anu_letivu=year)
	q = request.GET.get('q', '').strip()[:60]
	if q:
		qs = qs.filter(Q(nu_ref__icontains=q) | Q(de__icontains=q) | Q(para__icontains=q) | Q(asuntu__icontains=q))
	page = Paginator(qs, 50).get_page(request.GET.get('page'))
	years = list(Tama.objects.exclude(anu_letivu__isnull=True).values_list('anu_letivu', flat=True).distinct().order_by('-anu_letivu'))
	return render(request, 'kts/tama_list.html', {
		'title': ui.tr(lang, 'kts.in'), 'page': page, 'rows': _decorate(list(page.object_list), lang), 'status': status, 'year': year, 'q': q, 'years': years,
		'status_choices': [(s, 'kts.st.' + s) for s in STATUSES], 'can_register': roles.has_role(request.user, REGISTER)})


@roles.role_required(REGISTER)
def tama_add(request):
	lang = ui.lang(request)
	form = TamaForm(request.POST or None, request.FILES or None, lang=lang, today=_today())
	if request.method == 'POST' and form.is_valid():
		letter = services.register(form.save(commit=False), request.user)
		messages.success(request, ui.tr(lang, 'kts.msg.registered'))
		return redirect('kts-tama-detail', pk=letter.pk)
	return render(request, 'kts/form.html', {'title': ui.tr(lang, 'kts.in.add'), 'form': form, 'back': 'kts-tama'})


@roles.role_required(REGISTER)
def tama_edit(request, pk):
	lang = ui.lang(request)
	letter = get_object_or_404(Tama, pk=pk)
	if letter.status not in ('registered', 'returned'):
		messages.error(request, ui.tr(lang, 'kts.err.locked'))
		return redirect('kts-tama-detail', pk=pk)
	form = TamaForm(request.POST or None, request.FILES or None, instance=letter, lang=lang, today=_today())
	if request.method == 'POST' and form.is_valid():
		try:
			form.save()
			services.edited(pk, request.user)
			messages.success(request, ui.tr(lang, 'kts.msg.saved'))
			return redirect('kts-tama-detail', pk=pk)
		except services.LetterError as e:
			_fail(request, e)
	return render(request, 'kts/form.html', {'title': ui.tr(lang, 'kts.in.edit'), 'form': form, 'back': 'kts-tama', 'letter': letter})


def _can_view(request, letter):
	if roles.has_role(request.user, VIEW_ALL):
		return True
	mine = _mine(request)
	return bool(mine and letter.handler_id == mine.pk)


def tama_detail(request, pk):
	r = _guard(request)
	if r:
		return r
	letter = get_object_or_404(Tama.objects.select_related('handler', 'institutu', 'verified_by', 'disposed_by', 'done_by'), pk=pk)
	if not _can_view(request, letter):
		return render(request, 'home/403.html', status=403)
	lang = ui.lang(request)
	_decorate([letter], lang)
	events = list(letter.events.select_related('user', 'employee')[:60])
	for ev in events:
		ev.text = ui.tr(lang, 'kts.ev.' + ev.action)
		ev.to_text = ui.tr(lang, 'kts.st.' + ev.to_status) if ev.to_status else ''
	mine = _mine(request)
	is_handler = bool(mine and letter.handler_id == mine.pk)
	can_done = letter.status == 'disposed' and (is_handler or roles.has_role(request.user, DISPOSE))
	ctx = {'title': letter.nu_ref or '', 'letter': letter, 'events': events,
		'can_edit': roles.has_role(request.user, REGISTER) and letter.status in ('registered', 'returned'),
		'can_verify': roles.has_role(request.user, VERIFY) and letter.status == 'registered',
		'can_dispose': roles.has_role(request.user, DISPOSE) and letter.status in ('approved', 'disposed'),
		'can_done': can_done, 'overdue': bool(letter.due_date and letter.status == 'disposed' and letter.due_date < _today())}
	if ctx['can_dispose']:
		ctx['dispose_form'] = DisposeForm(initial={'handler': letter.handler_id, 'despacho': letter.despacho, 'due_date': letter.due_date}, lang=lang)
	if can_done:
		ctx['done_form'] = DoneForm(lang=lang)
	return render(request, 'kts/tama_detail.html', ctx)


def _step(role):
	"""POST-only, hanya peran `role`; kesalahan aturan ditampilkan sebagai pesan dan kembali ke halaman surat."""
	def deco(view):
		@require_POST
		@roles.role_required(role)
		def inner(request, pk):
			get_object_or_404(Tama, pk=pk)
			try:
				view(request, pk)
			except services.LetterError as e:
				_fail(request, e)
			return redirect('kts-tama-detail', pk=pk)
		inner.__name__ = view.__name__
		return inner
	return deco


@_step(VERIFY)
def tama_approve(request, pk):
	services.approve(pk, request.user, request.POST.get('note', ''))
	messages.success(request, ui.tr(request, 'kts.msg.approved'))


@_step(VERIFY)
def tama_return(request, pk):
	services.send_back(pk, request.user, request.POST.get('note', ''))
	messages.success(request, ui.tr(request, 'kts.msg.returned'))


@_step(DISPOSE)
def tama_dispose(request, pk):
	lang = ui.lang(request)
	form = DisposeForm(request.POST, lang=lang)
	if not form.is_valid():
		messages.error(request, ui.tr(lang, 'as.err.form'))
		return
	d = form.cleaned_data
	services.dispose(pk, request.user, d['handler'], d['despacho'], d['due_date'], today=_today())
	messages.success(request, ui.tr(lang, 'kts.msg.disposed'))


@require_POST
def tama_done(request, pk):
	r = _guard(request)
	if r:
		return r
	letter = get_object_or_404(Tama, pk=pk)
	mine = _mine(request)
	if not (roles.has_role(request.user, DISPOSE) or (mine and letter.handler_id == mine.pk)):
		return render(request, 'home/403.html', status=403)
	lang = ui.lang(request)
	form = DoneForm(request.POST, request.FILES, lang=lang)
	try:
		if not form.is_valid():
			raise services.LetterError('kts.err.note_required')
		services.finish(pk, request.user, form.cleaned_data['note'], form.cleaned_data.get('done_file'))
		messages.success(request, ui.tr(lang, 'kts.msg.done'))
	except services.LetterError as e:
		_fail(request, e)
	return redirect('kts-tama-detail', pk=pk)


@roles.role_required('ASSET_SELF_GROUPS')
def tama_mine(request):
	lang = ui.lang(request)
	mine = _mine(request)
	rows = _decorate(list(Tama.objects.filter(handler=mine).exclude(status='done').order_by('due_date', '-id')), lang) if mine else []
	done = _decorate(list(Tama.objects.filter(handler=mine, status='done').order_by('-done_at')[:20]), lang) if mine else []
	today = _today()
	for r in rows:
		r.overdue = bool(r.due_date and r.due_date < today)
	return render(request, 'kts/mine.html', {'title': ui.tr(lang, 'kts.mine'), 'rows': rows, 'done': done, 'emp': mine})


def _serve(request, letter, field):
	from django.contrib.auth.views import redirect_to_login
	if not request.user.is_authenticated:
		return redirect_to_login(request.get_full_path())
	f = getattr(letter, field)
	if not f:
		raise Http404
	try:
		handle = f.open('rb')
	except (FileNotFoundError, ValueError):
		raise Http404
	resp = FileResponse(handle, content_type='application/pdf', filename='kts-%d.pdf' % letter.pk)
	resp['Content-Disposition'] = 'inline; filename="kts-%d.pdf"' % letter.pk
	resp['X-Content-Type-Options'] = 'nosniff'
	resp['Cache-Control'] = 'private, no-store'
	return resp


@require_GET
def tama_file(request, pk, which='file'):
	r = _guard(request)
	if r:
		return r
	letter = get_object_or_404(Tama, pk=pk)
	if not _can_view(request, letter):
		return render(request, 'home/403.html', status=403)
	return _serve(request, letter, 'done_file' if which == 'done' else 'file_pdf')


# ------------------------------------------------------------------ surat keluar
@roles.role_required(VIEW_ALL)
def sai_list(request):
	lang = ui.lang(request)
	qs = Sai.objects.select_related('institutus')
	year = request.GET.get('year', '')
	if year.isdigit() and len(year) == 4:
		qs = qs.filter(anu_letivu=year)
	q = request.GET.get('q', '').strip()[:60]
	if q:
		qs = qs.filter(Q(nu_ref__icontains=q) | Q(de__icontains=q) | Q(para__icontains=q) | Q(asuntu__icontains=q))
	page = Paginator(qs, 50).get_page(request.GET.get('page'))
	years = list(Sai.objects.exclude(anu_letivu__isnull=True).values_list('anu_letivu', flat=True).distinct().order_by('-anu_letivu'))
	return render(request, 'kts/sai_list.html', {'title': ui.tr(lang, 'kts.out'), 'page': page, 'year': year, 'q': q, 'years': years,
		'can_out': roles.has_role(request.user, OUT)})


@roles.role_required(OUT)
def sai_add(request):
	lang = ui.lang(request)
	form = SaiForm(request.POST or None, request.FILES or None, lang=lang, today=_today())
	if request.method == 'POST' and form.is_valid():
		s = form.save(commit=False)
		import hashlib
		s.user, s.datetime, s.anu_letivu = request.user, timezone.now(), str(s.data_kartasai.year)
		s.save()
		s.hashed = hashlib.md5(str(s.pk).encode()).hexdigest()
		s.save(update_fields=['hashed'])
		messages.success(request, ui.tr(lang, 'kts.msg.registered'))
		return redirect('kts-sai-detail', pk=s.pk)
	return render(request, 'kts/form.html', {'title': ui.tr(lang, 'kts.out.add'), 'form': form, 'back': 'kts-sai'})


@roles.role_required(OUT)
def sai_edit(request, pk):
	lang = ui.lang(request)
	s = get_object_or_404(Sai, pk=pk)
	form = SaiForm(request.POST or None, request.FILES or None, instance=s, lang=lang, today=_today())
	if request.method == 'POST' and form.is_valid():
		obj = form.save(commit=False)
		obj.anu_letivu = str(obj.data_kartasai.year)
		obj.save()
		messages.success(request, ui.tr(lang, 'kts.msg.saved'))
		return redirect('kts-sai-detail', pk=pk)
	return render(request, 'kts/form.html', {'title': ui.tr(lang, 'kts.out.edit'), 'form': form, 'back': 'kts-sai', 'letter': s})


@roles.role_required(VIEW_ALL)
def sai_detail(request, pk):
	s = get_object_or_404(Sai.objects.select_related('institutus', 'user'), pk=pk)
	return render(request, 'kts/sai_detail.html', {'title': s.nu_ref or '', 's': s, 'can_out': roles.has_role(request.user, OUT)})


@require_GET
@roles.role_required(VIEW_ALL)
def sai_file(request, pk):
	return _serve(request, get_object_or_404(Sai, pk=pk), 'file_pdf')
