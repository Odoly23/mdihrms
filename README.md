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
python manage.py mdi_setup      # empat grup (admin/director/administrasaun/staff) + status F/P/L
python manage.py createsuperuser
python manage.py runserver
```
Tambahkan superuser ke grup `admin` lewat `/admin/`. Rahasia hanya di `.env` (diabaikan git).

## Produksi (cPanel VPS)
`DB_ENGINE=mysql` + `pip install -r requirements-mysql.txt`, `DEBUG=False`, `python manage.py collectstatic`.
Titik masuk Passenger: `passenger_wsgi.py`. Panduan lengkap absensi QR (kiosk, kartu, jaringan Starlink,
cPanel): [`attendance/QR_INSTALL.md`](attendance/QR_INSTALL.md).

PythonAnywhere: [`deploy/pythonanywhere/PANDUAN.md`](deploy/pythonanywhere/PANDUAN.md) (skrip `setup.sh` + berkas WSGI siap tempel).

## Tes
```bash
DEBUG=True python manage.py test        # tes: absensi QR + proyek
```

## Struktur organisasi (disederhanakan)
Hanya satu tingkat: **Program** (model `Division`), sesuai daftar staf MDI. `python manage.py mdi_setup` membuat dua program bawaan: *Program Nasional* dan
*ISIS - Programs ASEAN Think Tank*; program lain bisa ditambah lewat admin Django. Model DG (Diresaun Geral), Department, dan Section **dihapus** (beserta kolomnya di
absensi, kolokasaun, kontrak, dan data pegawai), sehingga formulir pegawai/kolokasaun hanya punya satu pilihan program dan halaman lebih cepat dimuat.
Migrasi `migrate` menghapus kolom lama tersebut (datanya hilang; **cadangkan database sebelum migrasi** bila ada data DG/Departemen yang masih dibutuhkan).
Akun baru yang dibuat dari form pegawai juga **wajib mengganti kata sandi** saat login pertama.

## Kecepatan database (indeks)
Mengikuti pelajaran "index gabungan": kolom yang dicari dengan `=` ditaruh **di depan**, kolom rentang di belakang, dan kolom tidak dibungkus fungsi (`DATE(kolom)`, `__year`).
Indeks gabungan: `Attendance(employee, date)` dan `(date)`, `ScanLog(employee, scanned_at)` dan `(code, scanned_at)`, `Leaves(employee, start_date, end_date)`,
`HealthClaim(employee, claim_date)`. Total klaim tahunan memakai rentang tanggal, bukan `claim_date__year`. Tes `IndexUsageTests` memeriksa rencana kueri memakai indeks.
Jalankan `python manage.py migrate` untuk membuatnya.

**Jangan langsung ke OLAP.** Tangga yang dipakai: (1) indeks (di atas); (2) cache laporan — bulan berjalan 60 dtk (`ATTENDANCE_REPORT_CACHE_SECONDS`), bulan yang sudah lewat 1 jam
(`ATTENDANCE_REPORT_CACHE_PAST_SECONDS`), dan dasbor memakai ulang rekap yang sama; (3) hilangkan N+1 (jumlah query tidak bertambah menurut jumlah pegawai, dijaga tes `ScalingTests`);
baru bila masih lambat: (4) replika baca / tabel ringkasan, dan paling akhir gudang data (OLAP). Scan absen (transaksi kecil) tidak memakai laporan, jadi tidak terganggu saat HRD membuka rekap.
Uji beban (500 pegawai × 1 tahun = 130 ribu baris absen, SQLite): rekap bulan 0,3-0,8 dtk dengan 5 query, papan hari ini 0,06 dtk dengan 3 query.

## Peran (empat grup)
| Grup | Bisa |
|---|---|
| `admin` (admin sistem) | **Kontrol penuh**: satu-satunya yang membuka PC kiosk, mengelola kartu QR, pengaturan absensi, menambah/mengubah funsionariu dan akun. Menyetujui klaim health care **milik direktur**. Boleh menggantikan administrasi/direktur pada alur surat. |
| `director` | **Melihat semua data** (absensi, dasbor hari ini, lisensa, daftar staf, aset, health care, surat). Menyetujui/menolak lisensa dan klaim health care staf, mengalokasikan staf ke posisi, **mendisposisi surat masuk (despacho)** dan **menyetujui surat keluar**. |
| `administrasaun` | **Membagi aset** (daftar, serah-terima, survei) dan **mengurus health care** (menandai dibayar). **Memverifikasi surat masuk dan surat keluar.** Melihat semua data (hanya baca). |
| `staff` (termasuk resepsionis) | Melihat data **sendiri** (absensi, lisensa, aset, klaim), **mengajukan lisensa dan klaim health care**, **mendaftarkan surat masuk**, membuat surat keluar. |

Grup lama (`president`, `hr`, `logistik`, `resepsionis`, `funsionario`, `employee`) dipindahkan otomatis oleh `python manage.py mdi_setup`
(president→director, hr/logistik→administrasaun, sisanya→staff). **Staf yang sebelumnya `staff` (bisa melihat absensi semua orang) kini hanya melihat
absensinya sendiri**; beri grup `administrasaun` bila perlu melihat semua. Penetapan grup dari jabatan:
`python manage.py mdi_assign_groups` (hanya menampilkan rencana) lalu `--apply`. Aturannya di `main/groups.py` (jabatan memuat *director* → director;
*adm*, *finans*, *logistik* → administrasaun; selainnya staff; admin sistem hanya diberikan manual). Akun baru untuk pegawai dibuat dengan grup menurut jabatannya.
Daftar staf (`Pegawai`) menampilkan dan menyaring berdasarkan grup. **Reset password** (hanya admin, tombol di baris pegawai yang punya akun): kata sandi menjadi kata sandi awal
(`mdi@#2026`, ganti lewat `DEFAULT_PASSWORD` di `.env`), sesi lama akun itu berakhir, dan saat login berikutnya pengguna **wajib langsung menggantinya** (halaman lain dialihkan; kata sandi awal tidak boleh dipakai lagi). Tindakan reset tercatat di log admin Django.

Lisensa yang disetujui otomatis dibaca oleh scan (status tetap *lisensa*). Penyetuju tidak bisa menyetujui lisensanya
sendiri. Ulang tahun hari ini muncul di Varanda dan di lonceng navbar (angka dicek tiap 60 detik, hanya saat tab
terlihat). Daftar grup per hak bisa diganti di `settings.py` (`MDI_*`, lihat `main/roles.py`).

## Konfigurasaun absensia (admin)
Menu **Absensia QR → Konfigurasaun** (`/attendance/config/`), mengikuti halaman lama: **Ativa tinan**, **Ativa fulan**, **Status absensia**,
**Feriadu nasionál**, dan **Tolerânsia** (keduanya berulang tiap tahun pada bulan/tanggal yang sama). Mengaktifkan tahun/bulan lewat POST. Sigla status F/P/L terkunci karena dipakai
absensi QR. Scan QR selalu memakai tanggal asli hari ini; libur dan hari toleransi yang aktif dianggap bukan hari kerja.
`python manage.py mdi_setup` mengisi 12 bulan dan tahun berjalan ±1.

## Aset dan survei status
Menu **ASET**: daftar barang (komputer, laptop, printer, monitor, telepon, scanner, dll.) dengan status **Foun** (baru), **Uza hela** (dipakai),
**Fila fali** (dikembalikan), **Hadi'a hela** (diperbaiki), **Estraga** (rusak), dan **Stok (di rak)**. Logistik/admin mendaftarkan, menyerahkan ke staf,
menerima kembali, dan menaruh di rak; setiap perubahan tercatat di riwayat (tidak bisa diubah). Staf melihat **aset miliknya** dan bisa menekan
"masih dipakai" atau "laporkan rusak" (survei mandiri). **Survei aset** menampilkan tabel kategori x status, stok di logistik, aset rusak/diperbaiki, aset
yang lama tidak dicek, dan ekspor CSV. HR dan direktur hanya melihat. Kategori bawaan dibuat oleh `mdi_setup`; kategori lain lewat `/admin/`.

## Health care (bonus saat sakit)
Menu **HEALTH CARE**: bonus **tetap US$ 50 per sakit** (ubah lewat `HEALTH_BONUS` di `.env`). Staf yang sakit mengajukan klaim dengan tanggal sakit dan dokumen
pendukung (surat dokter atau kuitansi, PDF/JPG/PNG maks. 5 MB; cuti sakit terkait opsional). Jumlah tidak diisi pengguna. Satu bonus per sakit: tanggal sakit atau
cuti sakit yang sama tidak bisa diklaim dua kali. **Klaim staf hanya disetujui/ditolak direktur (grup `director`); administrasi yang menandai dibayar**; HR tidak bisa, dan halaman admin Django
untuk klaim hanya-baca sehingga keputusan tidak bisa diubah dari sana. Admin dan direktur boleh menandai klaim yang sudah disetujui sebagai sudah dibayar; HR hanya melihat.
**Diagnosis tidak disimpan.** Bukti tidak punya URL publik: hanya pemilik klaim, HR, direktur, dan admin yang bisa mengunduhnya lewat tautan yang memeriksa hak akses.
**Klaim milik direktur sendiri hanya disetujui oleh admin** (direktur tidak bisa menyetujui klaimnya sendiri; admin tidak menyetujui klaim staf biasa).
Batas tahunan per pegawai (opsional): `HEALTH_ANNUAL_LIMIT=150` di `.env`.

## Surat masuk dan keluar (app `kts`)
Menu **KARTA**: dasbor dengan tombol **KARTA TAMA** (surat masuk) dan **KARTA SAI** (surat keluar).
**Surat masuk:** staf (termasuk resepsionis) mendaftarkan dengan PDF → **administrasi** memverifikasi dan menyetujui (atau mengembalikan dengan catatan) → **direktur**
mendisposisi ke satu penanggung jawab dengan *despacho* dan batas waktu opsional → penanggung jawab menyelesaikan dengan catatan hasil.
**Surat keluar:** **semua grup** boleh membuat → **administrasi** memverifikasi (tidak boleh surat buatannya sendiri) → **direktur** menyetujui; keduanya bisa mengembalikan
ke pembuat dengan catatan. Surat yang sudah disetujui terkunci. Staf biasa hanya melihat surat yang ia buat/daftarkan atau tangani; admin, direktur, dan administrasi melihat semuanya.
Setiap langkah tercatat (riwayat tidak bisa diubah), surat tidak bisa dihapus, PDF hanya lewat tautan yang memeriksa hak akses. `KTS_REQUIRE_PDF=False` di `.env` melonggarkan syarat PDF.
Lonceng navbar menghitung surat yang menunggu tindakan Anda.

## Dasbor absensi hari ini
Menu absensi **Dasbor hari ini** (`admin`, `director`, dan `administrasaun`): dua grafik di kiri (perbandingan hari ini dan per divisi) dan kartu `col-md-4` di kanan berisi daftar nama:
hadir tepat waktu (jam scan), terlambat (menit), izin, cuti, dan belum hadir. Halaman memuat ulang tiap menit. Jenis lisensa dihitung **cuti** bila kodenya ada di
`ATTENDANCE_CUTI_CODES` (bawaan `AL`, `CT`, `ANUAL`) atau namanya memuat cuti/anual/annual/férias; jenis lain dihitung **izin**. Daftar grup: `ATTENDANCE_BOARD_GROUPS`.

## Laporan keterlambatan
Menu absensi **Late**: per bulan, hari terlambat, total/rata-rata menit terlambat dan pulang lebih awal per pegawai (urut terlambat terbanyak), ekspor CSV.

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
CSV berkolom `nama,posisi,diresaun` (kolom `diresaun` = program/unit); tambahkan `--accounts` untuk sekaligus membuat akun login (nama.pengguna dari nama, kata sandi awal, wajib ganti, grup dari jabatan) (contoh: `employee/data/staff_example.csv`). Membuat funsionariu aktif, posisi, diresaun, dan
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
| `custom` | Division (satu-satunya unit organisasi, tampil sebagai **Program**), Position, wilayah, dll. |
| `employee` | Employee dan data pendukung + daftar staf untuk HR |
| `attendance` | Attendance, hari libur, **absensi QR** (`*_qr.py`, `templates/attendance/qr`) |
| `contract` | InitialContract, Contract, gaji, Kolokasaun + alokasi posisi |
| `leave` | Leaves, LeaveType, AnnualLeaves + pengajuan dan persetujuan lisensa |
| `kts` | Surat masuk (Tama) dengan alur verifikasi–disposisi, surat keluar (Sai) |
| `notif` | Lonceng notifikasi dan ulang tahun |
| `main` | `templates/main/`: `layout.html`, `topbar.html`, `navbar.html` (kerangka) + **satu menu per grup**: `adm.html`, `prezident.html` (director), `administrasaun.html`, `staff.html`, dengan potongan menu di `menu/`; `templates/home/`: `home`, `login`, `403/404/500`; `mdi_setup`, middleware wajib-ganti-sandi |
| `users` | Akun saya dan ganti kata sandi (`templates/auth/`) |
| `settings_app` | `upload_utils`, `utils`, `decorators` |
