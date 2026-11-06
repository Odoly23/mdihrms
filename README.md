# MDI-HRMS (mdihrms)

Sistem HRMS Mata Dalan Institute dengan **absensi kartu QR**: pegawai menempelkan kartu (QR di sisi belakang)
pada pembaca QR USB di PC pintu kantor; masuk/pulang tercatat otomatis.

Isi repositori ini disusun dari model dan kode yang diberikan (app `custom`, `employee`, `attendance`, `leave`,
`main`, `settings_app`). App lain di proyek lama (`contract`, `npp`, `mrjt`, `performance`, `training`, ...)
belum ada di sini.

## Menjalankan (percobaan)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # isi SECRET_KEY, ATTENDANCE_QR_SECRET; untuk percobaan: DEBUG=True
python manage.py migrate
python manage.py mdi_setup      # grup admin/staff/president/funsionario/employee + status F/P/L
python manage.py createsuperuser
python manage.py runserver
```
Tambahkan superuser ke grup `admin` lewat `/admin/`. Rahasia hanya di `.env` (diabaikan git).

## Produksi (cPanel VPS)
`DB_ENGINE=mysql` + `pip install -r requirements-mysql.txt`, `DEBUG=False`, `python manage.py collectstatic`.
Titik masuk Passenger: `passenger_wsgi.py`. Panduan lengkap absensi QR (kiosk, kartu, jaringan Starlink,
cPanel): [`attendance/QR_INSTALL.md`](attendance/QR_INSTALL.md).

## Tes
```bash
DEBUG=True python manage.py test        # 253 tes: absensi QR + proyek
```

## Peran (grup)
| Grup | Bisa |
|---|---|
| `admin` | Semuanya. **Satu-satunya** yang membuka PC kiosk, mengelola kartu QR, dan menambah/mengubah funsionariu (akun login dibuat otomatis dengan kata sandi acak yang tampil sekali). Admin juga wajib scan kartunya sendiri. |
| `president` (direktur) | Melihat rekap bulanan dan dashboard, **menyetujui/menolak lisensa**, **mengalokasikan staf ke posisi** (Kolokasaun). |
| `hr` | **Melihat semua** (absensi, lisensa, kolokasaun) dan daftar staf beserta detail masing-masing. Hanya baca. |
| `staff` | Melihat data absensi (hanya baca), melihat kolokasaun, **mengajukan lisensa** sendiri. |
| `funsionario`, `employee` | Laporan absensi sendiri dan mengajukan lisensa sendiri. |

Lisensa yang disetujui otomatis dibaca oleh scan (status tetap *lisensa*). Penyetuju tidak bisa menyetujui lisensanya
sendiri. Ulang tahun hari ini muncul di Varanda dan di lonceng navbar (angka dicek tiap 60 detik, hanya saat tab
terlihat). Daftar grup per hak bisa diganti di `settings.py` (`MDI_*`, lihat `main/roles.py`).

## Struktur
| App | Isi |
|---|---|
| `custom` | DG, Division, Department, Position, wilayah, dll. |
| `employee` | Employee dan data pendukung + daftar staf untuk HR |
| `attendance` | Attendance, hari libur, **absensi QR** (`*_qr.py`, `templates/attendance/qr`) |
| `contract` | InitialContract, Contract, gaji, Kolokasaun + alokasi posisi |
| `leave` | Leaves, LeaveType, AnnualLeaves + pengajuan dan persetujuan lisensa |
| `notif` | Lonceng notifikasi dan ulang tahun |
| `main` | Layout, navbar per grup, login, halaman galat, `mdi_setup` |
| `settings_app` | `upload_utils`, `utils`, `decorators` |
