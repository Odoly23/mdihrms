from django.contrib.auth.models import User
from django.db import models


class MustChangePassword(models.Model):
	"""Akun yang kata sandinya direset admin ke kata sandi awal: wajib mengganti sebelum memakai aplikasi."""
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='must_change')
	since = models.DateTimeField(auto_now_add=True)
	by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
