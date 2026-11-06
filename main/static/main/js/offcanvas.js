/* Sidebar offcanvas (layar kecil): buka/tutup dengan tombol, overlay, Esc, dan saat layar dilebarkan. */
(function () {
	var btn = document.getElementById('btnHam'), sb = document.getElementById('sidebar'), ov = document.getElementById('overlay');
	if (!btn || !sb || !ov) return;
	function open(on) {
		sb.classList.toggle('active', on);
		ov.classList.toggle('active', on);
		document.body.classList.toggle('sb-open', on);
		btn.setAttribute('aria-expanded', on ? 'true' : 'false');
		sb.setAttribute('aria-hidden', on ? 'false' : 'true');
		var icon = btn.querySelector('.fa'); if (icon) icon.className = on ? 'fa fa-times' : 'fa fa-bars';
		if (on) { var first = sb.querySelector('a,button'); if (first) first.focus({preventScroll: true}); } else if (document.activeElement && sb.contains(document.activeElement)) { btn.focus(); }
	}
	btn.addEventListener('click', function () { open(!sb.classList.contains('active')); });
	ov.addEventListener('click', function () { open(false); });
	sb.addEventListener('click', function (e) { if (e.target.closest('a')) open(false); });
	document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && sb.classList.contains('active')) open(false); });
	window.addEventListener('resize', function () { if (window.innerWidth >= 1200 && sb.classList.contains('active')) open(false); });
	sb.setAttribute('aria-hidden', 'true');
})();
