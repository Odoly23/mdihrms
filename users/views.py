"""Akun saya dan ganti kata sandi (semua pengguna yang masuk). Template: users/templates/auth/."""
from django import forms
from django.contrib import messages
from django.contrib.auth import password_validation, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from main import groups, middleware, roles, ui
from main.models import MustChangePassword


class PasswordForm(forms.Form):
	old = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}), max_length=128)
	new1 = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}), max_length=128)
	new2 = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}), max_length=128)

	def __init__(self, user, lang, *a, **kw):
		super().__init__(*a, **kw)
		self.user, self.lang = user, lang
		for f in self.fields.values():
			f.widget.attrs['class'] = 'form-control'
		ui.set_labels(self, lang, {'old': 'acc.pwd.old', 'new1': 'acc.pwd.new1', 'new2': 'acc.pwd.new2'})
		ui.localize_errors(self, lang)

	def clean(self):
		d = super().clean()
		if self.errors:
			return d
		if not self.user.check_password(d['old']):
			self.add_error('old', ui.tr(self.lang, 'acc.err.old'))
		elif d['new1'] != d['new2']:
			self.add_error('new2', ui.tr(self.lang, 'acc.err.mismatch'))
		elif d['new1'] == d['old'] or d['new1'] == settings.MDI_DEFAULT_PASSWORD:
			self.add_error('new1', ui.tr(self.lang, 'acc.err.same'))
		else:
			try:
				password_validation.validate_password(d['new1'], self.user)
			except ValidationError:
				self.add_error('new1', ui.tr(self.lang, 'acc.err.weak'))      # pesan validator Django (Inggris) diganti satu pesan 4 bahasa
		return d


@login_required
def account(request):
	lang = ui.lang(request)
	emp = roles.linked_employee(request.user)
	info = None
	if emp:
		from attendance import qr_service as svc
		info = svc.employee_info(emp, photo=False)
	have = set(request.user.groups.values_list('name', flat=True))
	mine = [g for g in groups.GROUPS if g in have]
	return render(request, 'auth/account.html', {'title': ui.tr(lang, 'acc.title'), 'emp': info, 'my_groups': mine,
		'u': request.user, 'is_super': request.user.is_superuser})


@login_required
@require_http_methods(['GET', 'POST'])
def password_change(request):
	lang = ui.lang(request)
	form = PasswordForm(request.user, lang, request.POST or None)
	if request.method == 'POST' and form.is_valid():
		request.user.set_password(form.cleaned_data['new1'])
		request.user.save(update_fields=['password'])
		update_session_auth_hash(request, request.user)          # tetap masuk di perangkat ini; sesi lain keluar
		MustChangePassword.objects.filter(user=request.user).delete()
		middleware.set_flag(request.user.pk, False)
		messages.success(request, ui.tr(lang, 'acc.pwd.done'))
		return redirect('account')
	forced = MustChangePassword.objects.filter(user=request.user).exists()
	return render(request, 'auth/change_password.html', {'title': ui.tr(lang, 'acc.pwd'), 'form': form, 'forced': forced})
