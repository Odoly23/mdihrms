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
DEBUG=True python manage.py test        # 318 tes: absensi QR + proyek
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

## Konfigurasaun absensia (admin)
Menu **Absensia QR → Konfigurasaun** (`/attendance/config/`), mengikuti halaman lama: **Ativa tinan**, **Ativa fulan**, **Status absensia**,
**Feriadu nasionál**, dan **Tolerânsia** (keduanya berulang tiap tahun pada bulan/tanggal yang sama). Mengaktifkan tahun/bulan lewat POST. Sigla status F/P/L terkunci karena dipakai
absensi QR. Scan QR selalu memakai tanggal asli hari ini; libur dan hari toleransi yang aktif dianggap bukan hari kerja.
`python manage.py mdi_setup` mengisi 12 bulan dan tahun berjalan ±1.

## Feriadu resmi Timor-Leste
```bash
python manage.py seed_holidays                 # 14 feriadu tetap (berulang tiap tahun) + Sexta Santa dan Korpu Kristi tahun ini dan 2 berikutnya
python manage.py seed_holidays --years 2028    # tambah tahun lain; --dry-run untuk simulasi
```
Aman diulang dan tidak menimpa isian admin. Sexta Santa (Jumat Agung) dan Korpu Kristi (Corpus Christi) dihitung dari tanggal Paskah dan
disimpan sebagai tanggal persis ("sekali saja"). **Idul Fitri dan Idul Adha** mengikuti kalender bulan: isi manual tiap tahun.
Daftar disusun dari kalender sekunder, bukan teks hukum: cocokkan dengan keputusan resmi RDTL lewat Konfigurasaun > Feriadu nasionál.

## Impor daftar staf
```bash
python manage.py import_staff data/staff_mdi.csv --dry-run     # simulasi: tidak menyimpan apa pun
python manage.py import_staff data/staff_mdi.csv               # impor; aman diulang (tidak menggandakan)
```
CSV berkolom `nama,posisi,diresaun` (contoh: `employee/data/staff_example.csv`). Membuat funsionariu aktif, posisi, diresaun, dan
kartu QR; tidak membuat akun login, NRF, tanggal lahir, atau kontak. Daftar asli berisi data pribadi: simpan di server,
jangan di git (pola `employee/data/staff_*.csv` sudah diabaikan).

## Tampilan dan bahasa
- Kerangka halaman: **topbar** (alamat/HP/email + bendera 4 bahasa), **navbar** menu, dan **sidebar offcanvas** di layar < 1200 px
  (tombol hamburger; menutup dengan overlay, Esc, atau memilih menu). CSS: `main/static/main/css/main.css`.
- Warna utama cukup diganti di satu variabel `--navy` pada `main.css` (sekarang merah logo MDI `#e3171e`).
- Seluruh halaman tersedia dalam Tetun, Inggris, Indonesia, Portugis; satu klik bendera mengganti semuanya. Teks ada di
  `attendance/qr_i18n.py` (absensi) dan `attendance/qr_i18n_ui.py` (halaman lain). Terjemahan Tetun/Portugis sebaiknya
  dibaca ulang penutur asli. Isi dari database (nama, jabatan, diresaun) tidak diterjemahkan.

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
