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
DEBUG=True python manage.py test        # 212 tes: absensi QR + proyek
```

## Struktur
| App | Isi |
|---|---|
| `custom` | DG, Division, Department, Position, wilayah, dll. |
| `employee` | Employee dan data pendukung |
| `attendance` | Attendance, hari libur, **absensi QR** (`*_qr.py`, `templates/attendance/qr`) |
| `leave` | Leaves, LeaveType, AnnualLeaves |
| `main` | Layout, navbar per grup, login, halaman galat, `mdi_setup` |
| `settings_app` | `upload_utils`, `utils`, `decorators` |
