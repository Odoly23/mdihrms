"""Pengaturan proyek MDI-HRMS. Semua rahasia dibaca dari environment / berkas .env (tidak ikut git)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

try:  # python-dotenv opsional: di cPanel variabel bisa diisi dari "Setup Python App"
	from dotenv import load_dotenv
	load_dotenv(BASE_DIR / '.env')
except ImportError:
	pass


def env(name, default=None, required=False):
	value = os.environ.get(name, default)
	if required and not value:
		raise RuntimeError('Variabel %s belum diisi (lihat .env.example)' % name)
	return value


def env_bool(name, default=False):
	return str(os.environ.get(name, default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
	return [x.strip() for x in str(os.environ.get(name, default)).split(',') if x.strip()]


DEBUG = env_bool('DEBUG', False)
SECRET_KEY = env('SECRET_KEY', 'dev-only-insecure-key' if DEBUG else None, required=True)
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')

INSTALLED_APPS = [
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'django.contrib.humanize',
	'custom',
	'main',
	'employee',
	'contract',
	'leave',
	'attendance',
	'assets',
	'health',
	'notif',
]

MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'whitenoise.middleware.WhiteNoiseMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mdihrms.urls'
WSGI_APPLICATION = 'mdihrms.wsgi.application'

TEMPLATES = [{
	'BACKEND': 'django.template.backends.django.DjangoTemplates',
	'DIRS': [],
	'APP_DIRS': True,
	'OPTIONS': {'context_processors': [
		'django.template.context_processors.debug',
		'django.template.context_processors.request',
		'django.contrib.auth.context_processors.auth',
		'django.contrib.messages.context_processors.messages',
		'main.context.nav',
	]},
}]

# Database: sqlite (percobaan) atau mysql (produksi). Kata sandi hanya dari .env.
if env('DB_ENGINE', 'sqlite') == 'mysql':
	DATABASES = {'default': {
		'ENGINE': 'django.db.backends.mysql',
		'NAME': env('DB_NAME', required=True),
		'USER': env('DB_USER', required=True),
		'PASSWORD': env('DB_PASSWORD', ''),
		'HOST': env('DB_HOST', 'localhost'),
		'PORT': env('DB_PORT', '3306'),
		'CONN_MAX_AGE': 60,
		'OPTIONS': {'init_command': "SET sql_mode='STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'", 'charset': 'utf8mb4'},
	}}
else:
	DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_PASSWORD_VALIDATORS = [
	{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
	{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
	{'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
	{'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Dili'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
	'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
	'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
X_FRAME_OPTIONS = 'SAMEORIGIN'

from django.contrib.messages import constants as message_constants  # noqa: E402
MESSAGE_TAGS = {message_constants.DEBUG: 'debug', message_constants.INFO: 'info',
	message_constants.SUCCESS: 'success', message_constants.WARNING: 'warning',
	message_constants.ERROR: 'danger'}

# Cache: file di disk lebih cocok di cPanel (beberapa proses Passenger berbagi isinya)
CACHES = {'default': {
	'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
	'LOCATION': str(BASE_DIR / 'cache'),
}}

import sys  # noqa: E402
if 'test' in sys.argv[:2]:      # tes tidak boleh menyentuh cache berkas milik aplikasi yang berjalan
	CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

if not DEBUG:
	SESSION_COOKIE_SECURE = env_bool('HTTPS', True)
	CSRF_COOKIE_SECURE = env_bool('HTTPS', True)
	SECURE_CONTENT_TYPE_NOSNIFF = True
	SECURE_SSL_REDIRECT = env_bool('SSL_REDIRECT', False)
	SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Topbar (dipakai bila lembaga aktif di custom.Institute belum punya datanya)
SITE_NAME = env('SITE_NAME', 'Mata Dalan Institute')
SITE_ADDRESS = env('SITE_ADDRESS', '')
SITE_PHONE = env('SITE_PHONE', '')
SITE_EMAIL = env('SITE_EMAIL', '')

# ---- Absensi QR (lihat attendance/QR_INSTALL.md) ----
ATTENDANCE_QR_SECRET = env('ATTENDANCE_QR_SECRET')
ATTENDANCE_NETWORK_MODE = env('ATTENDANCE_NETWORK_MODE', 'device')
ATTENDANCE_LANG_IN_NAVBAR = True
