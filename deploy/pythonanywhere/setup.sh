#!/usr/bin/env bash
# Pemasangan MDI-HRMS di PythonAnywhere. Jalankan SEKALI di "Bash console" PythonAnywhere:
#   bash ~/mdihrms/deploy/pythonanywhere/setup.sh
# Sebelumnya: git clone https://github.com/Odoly23/mdihrms ~/mdihrms   (repo privat: pakai token GitHub sebagai kata sandi)
# Aman dijalankan ulang (untuk memperbarui): tidak menimpa .env dan basis data.
set -euo pipefail

APP="$HOME/mdihrms"
VENV="$HOME/venv-mdihrms"
PY="${PYTHON_BIN:-python3.12}"          # sesuaikan dengan versi Python di tab Web (3.10 - 3.13)
USER_NAME="$(whoami)"
HOST="${USER_NAME}.pythonanywhere.com"

cd "$APP"
git pull --ff-only || true

[ -d "$VENV" ] || "$PY" -m venv "$VENV"
# shellcheck disable=SC1090
source "$VENV/bin/activate"
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

if [ ! -f .env ]; then
  SECRET="$(python -c 'import secrets;print(secrets.token_urlsafe(60))')"
  QR="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')"
  cat > .env <<EOF
SECRET_KEY=$SECRET
DEBUG=False
ALLOWED_HOSTS=$HOST
CSRF_TRUSTED_ORIGINS=https://$HOST
HTTPS=True
DB_ENGINE=sqlite
ATTENDANCE_QR_SECRET=$QR
ATTENDANCE_NETWORK_MODE=device
SITE_NAME=Mata Dalan Institute
HEALTH_BONUS=50
KTS_REQUIRE_PDF=True
ALLOW_CAMERA=True
EOF
  chmod 600 .env
  echo ">> .env dibuat (rahasia acak). SIMPAN salinan ATTENDANCE_QR_SECRET di tempat aman."
fi

python manage.py migrate --noinput
python manage.py mdi_setup
python manage.py collectstatic --noinput
mkdir -p media cache
python manage.py check --deploy || true

echo
echo "Selesai. Langkah berikutnya ada di deploy/pythonanywhere/PANDUAN.md (tab Web: WSGI, virtualenv, Static files, lalu Reload)."
echo "Buat akun admin pertama:  python manage.py createsuperuser"
