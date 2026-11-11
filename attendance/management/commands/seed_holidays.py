"""Isi feriadu nasionál Timor-Leste: tanggal tetap (berulang tiap tahun) dan feriadu movel yang dihitung per tahun.

    python manage.py seed_holidays                  # tahun ini dan 2 tahun berikutnya
    python manage.py seed_holidays --years 2027 2028
    python manage.py seed_holidays --dry-run

Aman diulang: tanggal yang sudah ada (milik admin sekalipun) tidak ditimpa atau digandakan.
PENTING: daftar ini disusun dari kalender sekunder (timeanddate, clockit), BUKAN dari teks hukum. Cocokkan dengan keputusan
resmi Pemerintah RDTL (Jornal da República) dan ubah/nonaktifkan lewat Absensia QR > Konfigurasaun > Feriadu nasionál.
Idul Fitri dan Idul Adha mengikuti kalender bulan: isi tiap tahun secara manual setelah ada pengumuman resmi."""
import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from attendance.models import NacionalHoliday

# (bulan, tanggal, nama Tetun, tahun referensi). Tahun = tahun peristiwa bila ada; selain itu 2000 sebagai tahun acuan.
FIXED = [
	(1, 1, 'Tinan Foun', 2000),
	(3, 3, 'Dia Veteranu', 2000),
	(5, 1, 'Dia Internasionál Traballadór', 2000),
	(5, 20, 'Dia Restaurasaun Independénsia', 2002),
	(8, 30, 'Dia Konsultasaun Popular', 1999),
	(11, 1, 'Loron Santu Hotu', 2000),
	(11, 2, 'Loron Finadu', 2000),
	(11, 3, 'Dia Nasionál Feto Timor', 2000),
	(11, 12, 'Masacre Santa Cruz (Dia Nasionál Juventude)', 1991),
	(11, 28, 'Dia Proklamasaun Independénsia', 1975),
	(12, 7, 'Dia Memória', 1975),
	(12, 8, 'Nossa Senhora da Imaculada Conceição', 2000),
	(12, 25, 'Natal', 2000),
	(12, 31, 'Dia Nasionál Eroi', 2000),
]


def easter(year):
	"""Domingo Paskah (kalender Gregorian, algoritma Meeus/Jones/Butcher)."""
	a, b, c = year % 19, year // 100, year % 100
	d, e = b // 4, b % 4
	f = (b + 8) // 25
	g = (b - f + 1) // 3
	h = (19 * a + b - d - g + 15) % 30
	i, k = c // 4, c % 4
	l = (32 + 2 * e + 2 * i - h - k) % 7
	m = (a + 11 * h + 22 * l) // 451
	month = (h + l - 7 * m + 114) // 31
	day = (h + l - 7 * m + 114) % 31 + 1
	return datetime.date(year, month, day)


def movable(year):
	"""[(tanggal, nama)] feriadu movel Kristen untuk satu tahun: Jumat Agung dan Corpus Christi."""
	e = easter(year)
	return [(e - datetime.timedelta(days=2), 'Sexta Santa'), (e + datetime.timedelta(days=60), 'Korpu Kristi')]


class Command(BaseCommand):
	help = 'Isi feriadu nasionál Timor-Leste (tanggal tetap + Jumat Agung + Corpus Christi per tahun).'

	def add_arguments(self, parser):
		parser.add_argument('--years', nargs='+', type=int, help='Tahun untuk feriadu movel (bawaan: tahun ini dan 2 berikutnya)')
		parser.add_argument('--dry-run', action='store_true')

	def handle(self, *args, **o):
		years = o['years'] or [datetime.date.today().year + n for n in range(3)]
		added = skipped = 0
		with transaction.atomic():
			for month, day, name, ref_year in FIXED:
				if NacionalHoliday.objects.filter(recurring=True, date__month=month, date__day=day).exists():
					skipped += 1
					self.stdout.write('ADA   %02d/%02d  %s' % (day, month, name))
					continue
				NacionalHoliday.objects.create(name=name, date=datetime.date(ref_year, month, day), recurring=True, is_active=True)
				added += 1
				self.stdout.write('BARU  %02d/%02d  %s (setiap tahun)' % (day, month, name))
			for year in sorted(set(years)):
				for d, name in movable(year):
					covered = (NacionalHoliday.objects.filter(recurring=False, date=d).exists()
							   or NacionalHoliday.objects.filter(recurring=True, date__month=d.month, date__day=d.day).exists())
					if covered:
						skipped += 1
						self.stdout.write('ADA   %s  %s' % (d.strftime('%d/%m/%Y'), name))
						continue
					NacionalHoliday.objects.create(name=name, date=d, recurring=False, is_active=True)
					added += 1
					self.stdout.write('BARU  %s  %s (tahun ini saja)' % (d.strftime('%d/%m/%Y'), name))
			if o['dry_run']:
				transaction.set_rollback(True)
		self.stdout.write(self.style.SUCCESS('%s: %d baru, %d sudah ada.' % ('SIMULASI' if o['dry_run'] else 'Selesai', added, skipped)))
		self.stdout.write('Cocokkan dengan keputusan resmi RDTL; tambahkan Idul Fitri/Idul Adha secara manual tiap tahun.')
