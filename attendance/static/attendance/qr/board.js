(function () {
	'use strict';
	/* Dasbor hari ini: muat ulang halaman tiap menit saat tab terlihat, agar daftar dan grafik selalu mutakhir. */
	setInterval(function () { if (!document.hidden) location.reload(); }, 60000);
})();
