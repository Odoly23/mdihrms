"""Alur surat masuk. Setiap perpindahan: satu transaksi, baris dikunci, dan satu baris riwayat. Hak akses diperiksa di view; aturan keadaan di sini."""
import datetime
import hashlib

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Tama, TamaEvent


class LetterError(Exception):
	def __init__(self, key, **params):
		super().__init__(key)
		self.key, self.params = key, params


def require_pdf():
	return bool(getattr(settings, 'MDI_KTS_REQUIRE_PDF', True))


def _log(letter, action, user, now, *, from_status='', to_status='', employee=None, note=''):
	TamaEvent.objects.create(letter=letter, action=action, from_status=from_status, to_status=to_status, user=user,
		employee=employee, note=(note or '')[:500], at=now)


def _lock(pk):
	return Tama.objects.select_for_update().get(pk=pk)


@transaction.atomic
def register(letter, user, now=None):
	"""Simpan surat masuk baru (oleh resepsionis): status 'registered'."""
	now = now or timezone.now()
	letter.status, letter.user, letter.datetime = 'registered', user, now
	letter.anu_letivu = str(letter.data_kartatama.year) if letter.data_kartatama else str(now.year)
	letter.save()
	letter.hashed = hashlib.md5(str(letter.pk).encode()).hexdigest()
	letter.save(update_fields=['hashed'])
	_log(letter, 'register', user, now, to_status='registered')
	return letter


@transaction.atomic
def edited(letter_id, user, note='', now=None):
	"""Dipanggil setelah resepsionis mengubah data: surat yang dikembalikan kembali ke antrean verifikasi."""
	now = now or timezone.now()
	l = _lock(letter_id)
	if l.status not in ('registered', 'returned'):
		raise LetterError('kts.err.locked')
	old = l.status
	if old == 'returned':
		l.status = 'registered'
		l.save(update_fields=['status'])
	_log(l, 'edit', user, now, from_status=old, to_status=l.status, note=note)
	return l


@transaction.atomic
def approve(letter_id, user, note='', now=None):
	"""Administrasi memverifikasi dan menyetujui (bila PDF wajib: harus ada lampiran)."""
	now = now or timezone.now()
	l = _lock(letter_id)
	if l.status != 'registered':
		raise LetterError('kts.err.state')
	if require_pdf() and not l.file_pdf:
		raise LetterError('kts.err.need_pdf')
	l.status, l.verified_by, l.verified_at, l.verify_note = 'approved', user, now, (note or '')[:300]
	l.save()
	_log(l, 'approve', user, now, from_status='registered', to_status='approved', note=note)
	return l


@transaction.atomic
def send_back(letter_id, user, note, now=None):
	"""Administrasi mengembalikan ke resepsionis untuk diperbaiki (catatan wajib)."""
	now = now or timezone.now()
	if not (note or '').strip():
		raise LetterError('kts.err.note_required')
	l = _lock(letter_id)
	if l.status != 'registered':
		raise LetterError('kts.err.state')
	l.status, l.verified_by, l.verified_at, l.verify_note = 'returned', user, now, note.strip()[:300]
	l.save()
	_log(l, 'return', user, now, from_status='registered', to_status='returned', note=note)
	return l


@transaction.atomic
def dispose(letter_id, user, handler, despacho, due_date=None, now=None, today=None):
	"""Direktur mendisposisi ke penanggung jawab dengan despacho. Boleh dialihkan selama belum selesai."""
	now = now or timezone.now()
	today = today or now.date()
	l = _lock(letter_id)
	if l.status not in ('approved', 'disposed'):
		raise LetterError('kts.err.state')
	if handler is None or handler.status_id != 1:
		raise LetterError('kts.err.handler')
	if not (despacho or '').strip():
		raise LetterError('kts.err.despacho')
	if due_date and due_date < today:
		raise LetterError('kts.err.due')
	action = 'dispose' if l.status == 'approved' else 'redispose'
	old = l.status
	l.status, l.handler, l.despacho, l.due_date = 'disposed', handler, despacho.strip(), due_date
	l.disposed_by, l.disposed_at = user, now
	l.save()
	_log(l, action, user, now, from_status=old, to_status='disposed', employee=handler, note=despacho)
	return l


@transaction.atomic
def finish(letter_id, user, note, done_file=None, now=None):
	"""Penanggung jawab (atau direktur) menyelesaikan surat: catatan hasil wajib, lampiran PDF opsional."""
	now = now or timezone.now()
	if not (note or '').strip():
		raise LetterError('kts.err.note_required')
	l = _lock(letter_id)
	if l.status != 'disposed':
		raise LetterError('kts.err.state')
	l.status, l.done_by, l.done_at, l.done_note = 'done', user, now, note.strip()[:500]
	if done_file:
		l.done_file = done_file
	l.save()
	_log(l, 'done', user, now, from_status='disposed', to_status='done', note=note)
	return l


def counts_for(user, employee, roles):
	"""Pekerjaan yang menunggu `user` (untuk dasbor dan lonceng): {'verify', 'dispose', 'handle', 'returned'}."""
	out = {'verify': 0, 'dispose': 0, 'handle': 0, 'returned': 0}
	if roles.has_role(user, 'KTS_VERIFY_GROUPS'):
		out['verify'] = Tama.objects.filter(status='registered').count()
	if roles.has_role(user, 'KTS_DISPOSE_GROUPS'):
		out['dispose'] = Tama.objects.filter(status='approved').count()
	if employee is not None:
		out['handle'] = Tama.objects.filter(status='disposed', handler=employee).count()
	if roles.has_role(user, 'KTS_REGISTER_GROUPS'):
		out['returned'] = Tama.objects.filter(status='returned').count()
	return out
