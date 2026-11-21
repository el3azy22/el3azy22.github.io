/* أسماء اللاعبين في كل تحديات المنصة (قرار إبراهيم 19 نوفمبر: «يتعمم في كل التحديات الحالية والقادمة»)
   مصدر واحد: mano/data.json (الاسم العربي + الإنجليزي) + mano/aliases.json (الأسماء المعروفة: ميلسون، بالا، كاكو…)
   - EL3P.ready            → Promise يخلص لما تنحمل البيانات (لو فشل التحميل: البحث يشتغل بالعربي بس)
   - EL3P.norm(s)          → توحيد الكتابة للبحث (همزات، تاء مربوطة، ألف مقصورة، تشكيل، مسافات، حروف صغيرة)
   - EL3P.keys(id)         → نص البحث للاعب: الإنجليزي + كل أسماءه المعروفة (موحد)
   - EL3P.match(q, id, ...names) → هل البحث q يطابق اللاعب (الأسماء العربية اللي عند الصفحة + الإنجليزي + المعروفة)
   - EL3P.known(id)        → الاسم المعروف بالعربي (أو '')
   - EL3P.label(id, name)  → «الاسم (المعروف)» للعرض، بدون تكرار لو الاسم فيه المعروف أصلاً
   id = رقم اللاعب في data.json (slug الرابطة). نفس المفتاح p[5] في tashkila/squads.json و k في rate.
   أي تحدي جديد فيه بحث أو أسماء لاعبين: يحمّل هالملف ويستخدمه بدال ما يكتب بحث خاص فيه. */
(function () {
  const base = (document.currentScript && document.currentScript.src || '').replace(/assets\/players\.js.*$/, '') || '/';
  const norm = s => String(s || '').replace(/[ً-ْـ]/g, '').replace(/[أإآ]/g, 'ا').replace(/ة/g, 'ه').replace(/ى/g, 'ي')
    .toLowerCase().replace(/\s+/g, '');
  const AR = /[؀-ۿ]/;
  const E = {}, AL = {};
  const ready = Promise.all([
    fetch(base + 'mano/data.json').then(r => r.json()),
    fetch(base + 'mano/aliases.json?v=' + Date.now().toString().slice(0, -5)).then(r => r.ok ? r.json() : {}).catch(() => ({}))
  ]).then(([d, al]) => {
    (d.players || []).forEach(p => { E[p.id] = p.e || '' });
    Object.keys(al || {}).forEach(k => { if (k !== '_' && Array.isArray(al[k])) AL[k] = al[k] });
  }).catch(() => {});
  const known = id => ((AL[id] || []).find(x => AR.test(x)) || '');
  const keys = id => norm((E[id] || '') + ' ' + (AL[id] || []).join(' '));
  const match = (q, id, ...names) => { const n = norm(q); if (!n) return true; return names.some(x => norm(x).includes(n)) || (!!id && keys(id).includes(n)) };
  const label = (id, name) => { const k = known(id); return k && !String(name || '').includes(k) ? `${name} (${k})` : String(name || '') };
  window.EL3P = { ready, norm, keys, match, known, label };
})();
