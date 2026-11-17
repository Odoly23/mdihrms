# Tempel isi berkas ini ke "WSGI configuration file" di tab Web PythonAnywhere
# (ganti seluruh isinya). Ubah USER bila nama akun PythonAnywhere Anda berbeda.
import os
import sys

path = '/home/USER/mdihrms'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'mdihrms.settings'   # rahasia dibaca dari /home/USER/mdihrms/.env

from django.core.wsgi import get_wsgi_application  # noqa: E402
application = get_wsgi_application()
