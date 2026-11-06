/* Pilihan diresaun/departamento/seksaun hanya yang termasuk induknya. Data dari <script type="application/json" id="j-div|j-dep|j-sec">. */
(function () {
	function J(id) { var el = document.getElementById(id); return el ? JSON.parse(el.textContent) : []; }
	var map = {
		id_division: {parent: 'id_dg', key: 'dg_id', rows: J('j-div')},
		id_department: {parent: 'id_division', key: 'division_id', rows: J('j-dep')},
		id_section: {parent: 'id_department', key: 'department_id', rows: J('j-sec')}
	};
	function apply(id) {
		var sel = document.getElementById(id), p = document.getElementById(map[id].parent);
		if (!sel || !p) return;
		var m = map[id], par = p.value, ok = {};
		m.rows.forEach(function (r) { if (!par || String(r[m.key]) === par) ok[r.id] = 1; });
		Array.prototype.forEach.call(sel.options, function (o) { o.hidden = !!o.value && !ok[o.value]; });
		if (sel.value && !ok[sel.value]) sel.value = '';
	}
	function all() { ['id_division', 'id_department', 'id_section'].forEach(apply); }
	['id_dg', 'id_division', 'id_department'].forEach(function (id) {
		var el = document.getElementById(id); if (el) el.addEventListener('change', all);
	});
	all();
})();
