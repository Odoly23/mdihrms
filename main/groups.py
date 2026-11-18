"""Empat grup pengguna MDI-HRMS dan pemetaan dari grup lama / jabatan.

  admin           admin sistem: kontrol penuh (kiosk, kartu, pengaturan, data funsionariu, akun)
  director        direktur: melihat semua data, menyetujui lisensa/klaim, mendisposisi surat masuk, menyetujui surat keluar
  administrasaun  administrasi: membagi aset, mengurus health care, memverifikasi surat masuk dan keluar
  staff           staf (termasuk resepsionis): melihat datanya, mengajukan lisensa, mendaftarkan surat masuk
"""
import re

from django.conf import settings

GROUPS = ['admin', 'director', 'administrasaun', 'staff']

# grup lama -> grup baru (dipakai mdi_setup untuk memindahkan keanggotaan, lalu grup lama dihapus bila kosong)
LEGACY = {'president': 'director', 'hr': 'administrasaun', 'logistik': 'administrasaun',
		  'resepsionis': 'staff', 'funsionario': 'staff', 'employee': 'staff'}

# aturan jabatan -> grup (huruf kecil; kata dicocokkan di awal kata). Yang pertama cocok menang; selebihnya 'staff'.
# 'admin' (admin sistem) sengaja TIDAK ada di sini: hak penuh hanya diberikan manual.
_POSITION_RULES = [('director', 'director'), ('direktur', 'director'), ('diretor', 'director'), ('direktor', 'director'),
				   ('adm', 'administrasaun'), ('finans', 'administrasaun'), ('keuangan', 'administrasaun'), ('logistik', 'administrasaun')]


def position_rules():
	return getattr(settings, 'MDI_POSITION_GROUPS', _POSITION_RULES)


def group_for_position(name):
	"""Grup yang cocok untuk nama jabatan (mis. 'Assistente Adm & Finansa' -> administrasaun); bawaan 'staff'."""
	text = (name or '').lower()
	for word, group in position_rules():
		if re.search(r'(?<![a-z])' + re.escape(word), text):
			return group
	return 'staff'


def ensure_groups():
	from django.contrib.auth.models import Group
	return {n: Group.objects.get_or_create(name=n)[0] for n in GROUPS}


def migrate_legacy():
	"""Pindahkan anggota grup lama ke grup baru, lalu hapus grup lama yang sudah kosong. Aman dijalankan berulang."""
	from django.contrib.auth.models import Group
	new = ensure_groups()
	moved = 0
	for old_name, target in LEGACY.items():
		old = Group.objects.filter(name=old_name).first()
		if not old:
			continue
		for u in old.user_set.all():
			u.groups.add(new[target])
			u.groups.remove(old)
			moved += 1
		if not old.user_set.exists():
			old.delete()
	return moved
