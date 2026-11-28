(function () {
	'use strict';
	/* Login: tampilkan/sembunyikan kata sandi, peringatan Caps Lock, tombol tidak bisa ditekan dua kali. */
	var pw = document.getElementById('id_password'), eye = document.getElementById('lg-eye');
	var caps = document.getElementById('lg-caps'), form = document.getElementById('lg-form'), btn = document.getElementById('lg-btn');
	if (eye && pw) {
		eye.addEventListener('click', function () {
			var show = pw.type === 'password';
			pw.type = show ? 'text' : 'password';
			eye.setAttribute('aria-pressed', show ? 'true' : 'false');
			eye.firstElementChild.className = show ? 'fa fa-eye-slash' : 'fa fa-eye';
			pw.focus();
		});
	}
	function capsCheck(ev) { if (caps && ev.getModifierState) caps.hidden = !ev.getModifierState('CapsLock'); }
	if (pw) { pw.addEventListener('keydown', capsCheck); pw.addEventListener('keyup', capsCheck); pw.addEventListener('blur', function () { if (caps) caps.hidden = true; }); }
	if (form && btn) form.addEventListener('submit', function () { setTimeout(function () { btn.disabled = true; }, 0); });
})();
