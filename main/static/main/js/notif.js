/* Lonceng notifikasi: tanya server tiap 60 detik, hanya saat tab terlihat (hemat server). */
(function () {
	var badge = document.getElementById('notifbadge');
	if (!badge) return;
	var url = badge.getAttribute('data-url'), timer = null, failures = 0;
	function set(id, v) { var el = document.getElementById(id); if (el) el.textContent = v; }
	function setAll(cls, v) { Array.prototype.forEach.call(document.querySelectorAll('.' + cls), function (el) { el.textContent = v; }); }
	function tick() {
		timer = null;
		if (document.hidden) return;
		fetch(url, {credentials: 'same-origin', headers: {'Accept': 'application/json'}})
			.then(function (r) { if (!r.ok) throw r.status; return r.json(); })
			.then(function (d) {
				failures = 0;
				setAll('notif-total', d.value > 0 ? d.value : '');
				set('notif-bday', d.birthdays); set('notif-leave', d.leaves);
				var n = document.getElementById('notif-names');
				if (n) n.textContent = d.names.length ? d.names.join(', ') : '';
			})
			.catch(function () { failures = Math.min(failures + 1, 4); })
			.then(function () { timer = setTimeout(tick, 60000 * Math.pow(2, failures)); });
	}
	document.addEventListener('visibilitychange', function () { if (!document.hidden && !timer) tick(); });
	tick();
})();
