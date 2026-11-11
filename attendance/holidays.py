"""Libur yang akan datang untuk pengumuman dan daftar. Libur nasional berulang tiap tahun pada bulan/tanggal yang sama
(tahun pada data = tahun peristiwa, mis. 12 Nov); hari toleransi mengikuti aturan scan (lihat qr_service.holiday_map)."""
import datetime

from . import qr_i18n as i18n
from . import qr_service as svc


def upcoming(today, days=90, limit=6, weekdays_only=False):
	"""[{date, kind, name, days_left, weekend}] dari `today` sampai `days` hari ke depan (hanya satu pembacaan cache)."""
	hol = svc.holiday_map_cached()
	out = []
	for n in range(days + 1):
		d = today + datetime.timedelta(days=n)
		hit = svc.holiday_for(hol, d)
		if not hit or (weekdays_only and d.weekday() >= 5):
			continue
		out.append({'date': d, 'kind': hit[0], 'name': hit[1], 'days_left': n, 'weekend': d.weekday() >= 5})
		if len(out) >= limit:
			break
	return out


def describe(item, lang):
	"""Teks siap tampil: tanggal lengkap, nama (atau jenisnya bila nama kosong), dan jarak hari."""
	n = item['days_left']
	return {
		'date_text': i18n.fmt_full(item['date'], lang),
		'name': item['name'] or i18n.tr(lang, 'hol.kind.' + item['kind']),
		'kind_text': i18n.tr(lang, 'hol.kind.' + item['kind']),
		'when': i18n.tr(lang, 'hol.today') if n == 0 else i18n.tr(lang, 'hol.tomorrow') if n == 1 else i18n.tr(lang, 'hol.in_days', n=n),
		'weekend': item['weekend'], 'days_left': n,
	}


def notice_data(today):
	"""Data mentah pengumuman (untuk layar kiosk, yang menerjemahkan sendiri di browser): libur hari ini atau besok."""
	for item in upcoming(today, days=1, limit=2, weekdays_only=True):
		return {'days_left': item['days_left'], 'date': item['date'].isoformat(), 'name': item['name'], 'kind': item['kind']}
	return None


def notice(today, lang):
	"""Pengumuman untuk semua pengguna: libur hari ini atau besok (hanya hari kerja, akhir pekan toh libur)."""
	data = notice_data(today)
	if not data:
		return None
	info = describe({'date': datetime.date.fromisoformat(data['date']), 'kind': data['kind'], 'name': data['name'],
					 'days_left': data['days_left'], 'weekend': False}, lang)
	key = 'hol.notice.today' if data['days_left'] == 0 else 'hol.notice.tomorrow'
	return {'text': i18n.tr(lang, key, date=info['date_text'], name=info['name']), 'today': data['days_left'] == 0}


def next_occurrence(d, today):
	"""Kemunculan berikutnya (hari ini atau sesudahnya) dari libur berulang; 29 Februari menjadi 28 Februari di tahun biasa."""
	for year in (today.year, today.year + 1, today.year + 2):
		try:
			cand = datetime.date(year, d.month, d.day)
		except ValueError:
			cand = datetime.date(year, 2, 28)
		if cand >= today:
			return cand
	return None
