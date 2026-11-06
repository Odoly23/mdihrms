from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from custom.models import AdministrativePost, Village


def _int(value):
	try:
		n = int(value)
	except (TypeError, ValueError):
		return None
	return n if 0 < n < 2 ** 31 else None


@login_required
def load_post(request):
	"""Pilihan Posto untuk satu Municipiu (dipakai dropdown berantai via AJAX)."""
	municipality_id = _int(request.GET.get('municipality'))
	post = AdministrativePost.objects.filter(municipality_id=municipality_id).order_by('name') if municipality_id else []
	return render(request, 'custom/post_dropdown.html', {'post': post})


@login_required
def load_village(request):
	"""Pilihan Suco untuk satu Posto."""
	post_id = _int(request.GET.get('administrativepost'))
	village = Village.objects.filter(administrativepost_id=post_id).order_by('name') if post_id else []
	return render(request, 'custom/village_dropdown.html', {'village': village})
