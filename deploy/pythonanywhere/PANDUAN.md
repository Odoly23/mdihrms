# Memasang MDI-HRMS di PythonAnywhere

Akun gratis cukup untuk uji coba (SQLite, satu aplikasi web `USER.pythonanywhere.com`). Untuk dipakai sungguhan sebaiknya akun berbayar
(domain sendiri, MySQL, tidak dimatikan otomatis). Kata sandi akun PythonAnywhere **jangan** dibagikan ke siapa pun, termasuk ke Claude.

## 1. Ambil kode dan jalankan skrip
Tab **Consoles → Bash**:
```bash
git clone https://github.com/Odoly23/mdihrms ~/mdihrms      # repo privat: kata sandi = token GitHub (Settings > Developer settings)
PYTHON_BIN=python3.12 bash ~/mdihrms/deploy/pythonanywhere/setup.sh
source ~/venv-mdihrms/bin/activate && cd ~/mdihrms && python manage.py createsuperuser
```
Skrip membuat virtualenv, memasang paket, membuat `.env` berisi `SECRET_KEY` dan `ATTENDANCE_QR_SECRET` acak, menjalankan migrasi,
`mdi_setup` (grup peran, bulan/tahun, kategori aset) dan `collectstatic`.

## 2. Tab Web
1. **Add a new web app → Manual configuration** → pilih versi Python yang sama dengan `PYTHON_BIN`.
2. **Virtualenv**: `/home/USER/venv-mdihrms`.
3. **Code → Source code / Working directory**: `/home/USER/mdihrms`.
4. **WSGI configuration file**: ganti seluruh isi dengan `deploy/pythonanywhere/wsgi_pythonanywhere.py` (ubah `USER`).
5. **Static files**: URL `/static/` → Directory `/home/USER/mdihrms/staticfiles`. (Jangan petakan `/media/`: berkas pribadi hanya lewat halaman yang memeriksa hak akses.)
6. **Force HTTPS**: Enabled. Klik **Reload**.

## 3. Setelah hidup
- Buka `https://USER.pythonanywhere.com/`, masuk sebagai superuser, tambahkan akun ke grup (`admin`, `president`, `resepsionis`, dst.).
- Di PC kiosk, login sebagai admin → **Perangkat kiosk** → pasangkan PC (mode `device` cocok untuk IP Starlink yang berganti-ganti).
- Setiap kali kode diperbarui: `bash ~/mdihrms/deploy/pythonanywhere/setup.sh`, lalu **Reload** di tab Web.

## 4. Catatan khusus PythonAnywhere
- Zona waktu server tidak dipakai: aplikasi memakai `Asia/Dili`.
- Akun gratis: koneksi keluar dibatasi dan aplikasi dinonaktifkan bila tidak di-**Extend** tiap 3 bulan. Basis data SQLite ada di `~/mdihrms/db.sqlite3`: **cadangkan** (Files → unduh) secara rutin, juga folder `media/` (PDF surat, bukti health care, foto).
- MySQL (berbayar): buat basis data di tab **Databases**, lalu di `.env`: `DB_ENGINE=mysql`, `DB_NAME=USER$mdihrms`, `DB_USER=USER`, `DB_PASSWORD=...`, `DB_HOST=USER.mysql.pythonanywhere-services.com`, dan `pip install -r requirements-mysql.txt`.
- Kamera kiosk dan pembaca USB butuh HTTPS, yang sudah disediakan PythonAnywhere.
- Log galat: tab Web → Error log.
