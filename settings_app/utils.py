import hashlib
from calendar import monthrange
import datetime


def getnewid(table_name):
	result = table_name.objects.last()
	newid = result.id + 1 if result else 1
	return newid, hashlib.md5(str(newid).encode()).hexdigest()


def hash_md5(strhash):
	return hashlib.md5(strhash.encode()).hexdigest()


def hash_sha256(strhash):
	return hashlib.sha256(strhash.encode()).hexdigest()


def split_string(string):
	return string.split()[0].lower()


_TET = ['Janeiru', 'Fevereiru', 'Marsu', 'Abril', 'Maiu', 'Junhu', 'Julhu', 'Agostu', 'Setembru',
	'Outubru', 'Novembru', 'Dezembru']
_POR = ['Janeiro', 'Fevereiro', 'Marco', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro',
	'Outubro', 'Novembro', 'Desembro']
_ENG = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
	'October', 'November', 'December']


def f_monthname(month):
	return _TET[month - 1]


def f_monthname_por(month):
	return _POR[month - 1]


def f_monthname_eng(month):
	return _ENG[month - 1]


def f_monthlist():
	return [[i + 1, name] for i, name in enumerate(_ENG)]


def number_of_days_in_month(year=2019, month=2):
	return monthrange(year, month)[1]


def f_card_expiry(start_date):
	d = datetime.datetime.strptime(str(start_date), "%Y-%m-%d")
	try:
		return datetime.date(d.year + 4, d.month, d.day).strftime("%Y-%m-%d")
	except ValueError:  # 29 Februari
		return datetime.date(d.year + 4, d.month, 28).strftime("%Y-%m-%d")


def f_date_interval(start_date, end_date):
	d1 = datetime.datetime.strptime(str(start_date), "%Y-%m-%d")
	d2 = datetime.datetime.strptime(str(end_date), "%Y-%m-%d")
	return d2 - d1
